import os
import logging
from random import random
import socket
import threading
import wsgiref.simple_server


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
