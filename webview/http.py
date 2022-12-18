import bottle
import json
import logging
import os
import threading
import random
import socket
import uuid

from .util import abspath, is_app, is_local_url


logger = logging.getLogger(__name__)


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


class BottleServer(object):
    def __init__(self):
        self.root_path='/'
        self.running = False
        self.address = None
        self.js_callback = None
        self.js_api_endpoint = None
        self.uid = str(uuid.uuid1())


    @classmethod
    def start_server(self, urls, http_port):
        from webview import _debug
        
        #import pudb; pu.db
        
        apps = [u for u in urls if is_app(u)]
        local_urls = [u for u in urls if is_local_url(u)]
        common_path = os.path.dirname(os.path.commonpath(local_urls)) if len(local_urls) > 0 else None
        
        server = self()
        server.root_path = abspath(common_path) if common_path is not None else None

        apiApp = bottle.Bottle()
        @apiApp.post(f'/js_api/{server.uid}')
        def js_api():
            bottle.response.headers['Access-Control-Allow-Origin'] = '*'
            bottle.response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
            bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            body = json.loads(bottle.request.body.read().decode('utf-8'))
            if js_callback:
                return json.dumps(js_callback(body))
            else:
                logger.error('JS callback function is not set')


        @apiApp.route('/')
        @apiApp.route('/<file:path>')
        def asset(file):
            if not server.root_path:
                return ''
            bottle.response.set_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            bottle.response.set_header('Pragma', 'no-cache')
            bottle.response.set_header('Expires', 0)
            return bottle.static_file(file, root=server.root_path)

        app = apiApp
        server.port = http_port or _get_random_port()
        server.thread = threading.Thread(target=lambda: bottle.run(app=app,port=server.port, quiet=not _debug), daemon=True)
        server.thread.start()

        server.running = True
        server.address = f'http://127.0.0.1:{server.port}/'
        server.js_api_endpoint = f'{server.address}js_api/{server.uid}'

        return server.address, common_path, server


def start_server(urls,http_port,server=BottleServer,**serverArgs):
    server = server if not server is None else BottleServer
    return server.start_server(urls,http_port,**serverArgs)

