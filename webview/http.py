from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

if sys.platform == 'win32' and ('pythonw.exe' in sys.executable or getattr(sys, 'frozen', False)):
    # sys.stdout and sys.stderr are None on Windows with pythonw.exe or PyInstaller >= 5.8.0.
    # wsgiref writes request logs to sys.stderr and passes it to applications as wsgi.errors.
    if sys.stderr is None:  # type: ignore
        sys.stderr = open(os.devnull, 'w')
    if sys.stdout is None:  # type: ignore
        sys.stdout = open(os.devnull, 'w')


import logging
import ssl
import threading
import uuid
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import bottle
from typing_extensions import TypedDict, Unpack

from .util import abspath, is_app, is_local_url

logger = logging.getLogger('pywebview')
global_server = None


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs) -> None:
        pass


class BottleServer:
    def __init__(self) -> None:
        self.root_path: str | None = '/'
        self.running = False
        self.address: str = ''
        self.uid = str(uuid.uuid4())
        self.common_path: str | None = None
        self.port: int = 0
        self.thread: threading.Thread | None = None

    @classmethod
    def start_server(
        cls,
        urls: list[str | Callable[..., Any]],
        http_port: int | None,
        keyfile: None = None,
        certfile: None = None,
    ) -> tuple[str, str | None, BottleServer]:
        from webview import _state

        apps = [u for u in urls if is_app(u)]
        server = cls()
        common_path: str | None

        if len(apps) > 0:
            app = apps[0]
            common_path = '.'
        else:
            local_urls = [u.split('#')[0] for u in urls if is_local_url(u)]
            common_path = os.path.commonpath(local_urls) if len(local_urls) > 0 else None
            if common_path is not None and not os.path.isdir(abspath(common_path)):
                common_path = os.path.dirname(common_path)
            logger.debug(f'Common path for local URLs: {common_path}')
            server.root_path = abspath(common_path) if common_path is not None else None
            logger.debug(f'HTTP server root path: {server.root_path}')
            app = bottle.Bottle()

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

        # Port 0 lets the OS assign a free port
        httpd = make_server(
            '127.0.0.1',
            http_port or 0,
            app,
            server_class=_ThreadingWSGIServer,
            handler_class=WSGIRequestHandler if _state['debug'] else _QuietHandler,
        )

        if keyfile and certfile:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.load_cert_chain(certfile, keyfile)
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

        server.port = httpd.server_port
        server.thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server.thread.start()

        server.running = True
        protocol = 'https' if keyfile and certfile else 'http'
        server.address = f'{protocol}://127.0.0.1:{server.port}/'
        server.common_path = common_path

        return server.address, common_path, server

    @property
    def is_running(self) -> bool:
        return self.running


class ServerArgs(TypedDict, total=False):
    keyfile: None
    certfile: None


def start_server(
    urls: list[str | Callable[..., Any]],
    http_port: int | None = None,
    server: type[BottleServer] = BottleServer,
    **server_args: Unpack[ServerArgs],
) -> tuple[str, str | None, BottleServer]:
    server = server if server is not None else BottleServer
    return server.start_server(urls, http_port, **server_args)


def start_global_server(
    http_port: int | None = None,
    urls: list[str | Callable[..., Any]] = ['.'],
    server: type[BottleServer] = BottleServer,
    **server_args: Unpack[ServerArgs],
) -> tuple[str, str | None, BottleServer]:
    global global_server
    address, common_path, global_server = start_server(
        urls=urls, http_port=http_port, server=server, **server_args
    )
    return address, common_path, global_server
