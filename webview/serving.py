import http.server
import logging
import os
import pathlib
import random
import socket
import threading
import urllib.parse
import wsgiref.simple_server
import wsgiref.util

from .util import abspath
from .wsgi import StaticFiles

__all__ = ('resolve_url',)


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


class WSGIRequestHandler11(wsgiref.simple_server.WSGIRequestHandler):
    protocol_version = 'HTTP/1.1'


if hasattr(http.server, 'ThreadingHTTPServer'):
    # Python 3.7+
    class ThreadingWSGIServer(http.server.ThreadingHTTPServer, wsgiref.simple_server.WSGIServer):
        pass
else:
    # Python 3.6 and earlier
    ThreadingWSGIServer = wsgiref.simple_server.WSGIServer


def get_wsgi_server(app):
    if hasattr(app, '__webview_url'):
        # It's already been spun up and is running
        return app.__webview_url

    port = _get_random_port()
    server = wsgiref.simple_server.make_server(
        'localhost', port, app, server_class=ThreadingWSGIServer,
        handler_class=WSGIRequestHandler11,
    )

    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

    app.__webview_url = 'http://localhost:{0}/'.format(port)
    logger.debug('HTTP server for {!r} started on {}'.format(app, app.__webview_url))

    return app.__webview_url


_path_apps = {}


def resolve_url(url, should_serve):
    """
    Given a URL-ish thing and a bool, return a real URL.

    * url: A URL, a path-like, a string path, or a wsgi app
    * should_serve: Should we start a server

    Note that if given a wsgi app, a server will always be started.
    """
    if isinstance(url, str):
        bits = urllib.parse.urlparse(url)
    else:
        # To create an empty version of the struct
        bits = urllib.parse.urlparse("")

    if url is None:
        return None

    elif bits.scheme and bits.scheme != 'file':
        # an http, https, etc URL
        return url

    elif hasattr(url, '__fspath__') or isinstance(url, str):
        # A local path

        # 1. Resolve the several options into an actual path
        if hasattr(url, '__fspath__'):
            path = os.fspath(url)
        elif bits.scheme == 'file':
            path = os.path.dirname(bits.netloc or bits.path)
        else:
            path = url

        # If it's a relative path, resolve it relative to the app root
        path = abspath(path)

        # If we have not been asked to serve local paths, bail
        if not should_serve:
            # using pathlib for this because it turns out file URLs are full of dragons
            return pathlib.Path(path).as_uri()

        if os.path.isdir(path):
            rootdir = path
            homepage = None
        else:
            rootdir, homepage = os.path.split(path)
        # Get/Build a WSGI app to serve the path and spin it up
        if path not in _path_apps:
            _path_apps[path] = StaticFiles(rootdir)
        url = get_wsgi_server(_path_apps[path])

        if homepage is not None:
            url = urllib.parse.urljoin(url, homepage)

        return url

    elif callable(url):
        # A wsgi application
        return get_wsgi_server(url)

    else:
        raise TypeError("Cannot resolve {!r} into a URL".format(url))
