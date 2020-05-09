import os
import logging
import pathlib
from random import random
import socket
import threading
import urllib.parse
import wsgiref.simple_server

from .util import get_app_root


__all__ = ('resolve_url',)

logger = logging.getLogger('pywebview')


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


def start_server(url):
    port = _get_random_port()
    server = wsgiref.simple_server.make_server('localhost', port, wsgiref.simple_server.demo_app)

    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

    new_url = 'http://localhost:{0}/{1}'.format(port, os.path.basename(url))
    logger.debug('HTTP server started on http://localhost:{0}'.format(port))

    return new_url


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
            return pathlib.Path(path).as_uri()

        # Get/Build a WSGI app to serve the path and spin it up
        app = wsgiref.simple_server.demo_app  # TODO
        return get_wsgi_server(app)
    elif callable(url):
        # A wsgi application
        return get_wsgi_server(url)
    else:
        raise TypeError("Cannot resolve {!r} into a URL".format(url))
