import os
import sys


if sys.platform == 'win32' and ('pythonw.exe' in sys.executable or getattr(sys, 'frozen', False)):
    # bottle.py versions prior to 0.12.23 (the latest on PyPi as of Feb 2023) require stdout and
    # stderr to exist, which is not the case on Windows with pythonw.exe or PyInstaller >= 5.8.0
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')


import bottle
import json
import logging
import threading
import random
import ssl
import socket
import uuid
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
from socketserver import ThreadingMixIn
from .util import abspath, is_app, is_local_url


logger = logging.getLogger(__name__)

global_server = None


def _get_random_port():
    while True:
        port = random.randint(1023, 65535)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
            except OSError:
                logger.warning('Port %s is in use' % port)
                continue
            else:
                return port


class ThreadedAdapter(bottle.ServerAdapter):
    def run(self, handler):
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw):
                    pass

            self.options['handler_class'] = QuietHandler

        class ThreadAdapter(ThreadingMixIn, WSGIServer):
            pass

        server = make_server(self.host, self.port, handler, server_class=ThreadAdapter, **self.options)
        server.serve_forever()


class BottleServer(object):
    def __init__(self):
        self.root_path='/'
        self.running = False
        self.address = None
        self.js_callback = {}
        self.js_api_endpoint = None
        self.uid = str(uuid.uuid1())

    @classmethod
    def start_server(self, urls, http_port, keyfile=None, certfile=None):
        from webview import _debug

        apps = [u for u in urls if is_app(u)]
        server = self()

        if len(apps) > 0:
            app = apps[0]
            common_path = '.'
        else:
            local_urls = [u for u in urls if is_local_url(u)]
            common_path = os.path.dirname(os.path.commonpath(local_urls)) if len(local_urls) > 0 else None
            server.root_path = abspath(common_path) if common_path is not None else None
            app = bottle.Bottle()

            @app.post(f'/js_api/{server.uid}')
            def js_api():
                bottle.response.headers['Access-Control-Allow-Origin'] = '*'
                bottle.response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
                bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

                body = json.loads(bottle.request.body.read().decode('utf-8'))
                if body['uid'] in server.js_callback:
                    return json.dumps(server.js_callback[body['uid']](body))
                else:
                    logger.error('JS callback function is not set for window %s' % body['uid'])

            @app.route('/')
            @app.route('/<file:path>')
            def asset(file):
                if not server.root_path:
                    return ''
                bottle.response.set_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                bottle.response.set_header('Pragma', 'no-cache')
                bottle.response.set_header('Expires', 0)
                return bottle.static_file(file, root=server.root_path)

        server.root_path = abspath(common_path) if common_path is not None else None
        server.port = http_port or _get_random_port()
        if keyfile and certfile:
          server_adapter = SSLWSGIRefServer()
          server_adapter.port = server.port
          setattr(server_adapter, 'pywebview_keyfile', keyfile)
          setattr(server_adapter, 'pywebview_certfile', certfile)
        else:
         server_adapter = ThreadedAdapter
        server.thread = threading.Thread(target=lambda: bottle.run(app=app, server=server_adapter, port=server.port, quiet=not _debug['mode']), daemon=True)
        server.thread.start()

        server.running = True
        protocol = 'https' if keyfile and certfile else 'http'
        server.address = f'{protocol}://127.0.0.1:{server.port}/'
        self.common_path = common_path
        server.js_api_endpoint = f'{server.address}js_api/{server.uid}'

        return server.address, common_path, server
    
    @property
    def is_running(self):
        return self.running

class SSLWSGIRefServer(bottle.ServerAdapter):
    def run(self, app):  # pragma: no cover
        from wsgiref.simple_server import make_server
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self):  # Prevent reverse DNS lookups please.
                return self.client_address[0]

            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', WSGIServer)

        if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:

                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        self.srv = make_server(self.host, self.port, app, server_cls,
                               handler_cls)
        context = ssl.create_default_context()
        self.srv.socket = ssl.wrap_socket(
                self.srv.socket,
                keyfile=self.pywebview_keyfile,
                certfile=self.pywebview_certfile,
                server_side=True)
        self.port = self.srv.server_port  # update port actual port (0 means random)
        os.unlink(self.pywebview_keyfile)
        try:
            self.srv.serve_forever()
        except KeyboardInterrupt:
            self.srv.server_close()  # Prevent ResourceWarning: unclosed socket
            raise


def start_server(urls, http_port=None, server=BottleServer, **server_args):
    server = server if not server is None else BottleServer
    return server.start_server(urls, http_port, **server_args)


def start_global_server(http_port=None, urls='.', server=BottleServer, ssl=False, **server_args):
    global global_server
    address, common_path, global_server = start_server(urls=urls, http_port=http_port, server=server, **server_args)
    return address, common_path, global_server

