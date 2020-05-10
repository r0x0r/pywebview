import os
import logging
import pathlib
import posixpath
from random import random
import socket
import threading
import urllib.parse
import wsgiref.simple_server

from .util import get_app_root


__all__ = ('resolve_url', 'StaticFiles', 'StaticResources', 'Routing')

logger = logging.getLogger(__name__)


class Routing(dict):
    """
    Implements a basic URL routing system.

    Path prefixes are compared to the request path. The longest prefix wins.

    Example:
        Routing({
            '/': app,
            '/static': Static('mystatic'),
        })
    """

    def no_route_app(self, environ, start_response):
        """
        Filler app to handle if routing fails
        """
        urlpath = environ['SCRIPT_NAME'] + environ['PATH_INFO']

        status = '404 Not Found'
        response_body = "Path {} was not found".format(urlpath)

        response_headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(response_body)))
        ]

        start_response(status, response_headers)
        return [response_body]

    def __call__(self, environ, start_response):
        # SCRIPT_NAME + PATH_INFO = full url
        urlpath = environ['SCRIPT_NAME'] + environ['PATH_INFO']
        if not urlpath:
            urlpath = '/'

        potentials = [
            prefix
            for prefix in self.keys()
            if posixpath.commonpath([prefix, urlpath]) == prefix
        ]
        try:
            match = max(potentials, key=len)
        except ValueError:
            # max() got an empty list, aka no matches found
            return self.no_route_app(environ, start_response)

        app = self[match]
        environ['SCRIPT_NAME'] = urlpath[:len(match)]
        environ['PATH_INFO'] = urlpath[len(match):]

        return app(environ, start_response)


def _get_random_port():
    def random_port():
        port = int(random() * 64512 + 1023)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            sock.bind(('localhost', port))
        except OSError:
            logger.warning('Port %s is in use' % port)
            return None
        else:
            return port
        finally:
            sock.close()

    for port in iter(random_port, ...):
        if port is not None:
            return port


def get_wsgi_server(app):
    if hasattr(app, '__webview_url'):
        # It's already been spun up and is running
        return app.__webview_url

    port = _get_random_port()
    server = wsgiref.simple_server.make_server('localhost', port, app)

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
        bits = urllib.parse.urlparse("")

    if bits.scheme not in 'file':
        # an http, https, etc URL
        return url
    elif hasattr(url, '__fspath__') or isinstance(url, str):
        # A local path

        # 1. Resolve the several options into an actual path
        if hasattr(url, '__fspath__'):
            path = os.fspath(url)
        elif bits.scheme == 'file':
            path = bits.path
        else:
            path = url

        # If it's a relative path, resolve it relative to the app root
        if not os.path.isabs(path):
            path = os.path.join(get_app_root())

        # If we have not been asked to serve local paths, bail
        if not should_serve:
            # using pathlib for this because it turns out file URLs are full of dragons
            return pathlib.Path(path).as_uri()

        # Get/Build a WSGI app to serve the path and spin it up
        if path not in _path_apps:
            _path_apps[path] = wsgiref.simple_server.demo_app  # TODO
        return get_wsgi_server(_path_apps[path])
    elif callable(url):
        # A wsgi application
        return get_wsgi_server(url)
    else:
        raise TypeError("Cannot resolve {!r} into a URL".format(url))
