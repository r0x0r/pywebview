import bottle
import logging
import os
import threading
import random
import socket

from .util import abspath, is_local_url

logger = logging.getLogger(__name__)
root_path='/'
running = False

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


class QuietWSGIRefServer(bottle.WSGIRefServer):
    quiet = False


@bottle.route('/')
@bottle.route('/<file:path>')
def asset(file):
    return bottle.static_file(file, root=root_path)


def start_server(urls):
    def _run():
        bottle.run(server=QuietWSGIRefServer, port=port)

    global root_path, running
    url = [u for u in urls if is_local_url(u)][0]
    root_path = os.path.dirname(abspath(url))

    port = _get_random_port()
    t = threading.Thread(target=lambda: bottle.run(server=QuietWSGIRefServer, port=port), daemon=True)
    t.start()

    running = True
    prefix = f'http://127.0.0.1:{port}/'

    return prefix


