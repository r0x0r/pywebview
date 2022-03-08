import bottle
import json
import logging
import os
import threading
import random
import socket
import uuid


from .util import abspath, is_local_url

logger = logging.getLogger(__name__)
root_path='/'
running = False

address = None
js_callback = None
js_api_endpoint = None
uid = str(uuid.uuid1())

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


@bottle.post(f'/js_api/{uid}')
def js_api():
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'
    bottle.response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
    bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

    body = json.loads(bottle.request.body.read().decode('utf-8'))
    if js_callback:
        return json.dumps(js_callback(body))
    else:
        logger.error('JS callback function is not set')

print(f'/js_api/{uid}')


@bottle.route('/')
@bottle.route('/<file:path>')
def asset(file):
    if not root_path:
        return ''
    bottle.response.set_header('Cache-Control', 'no-cache, no-store, must-revalidate')
    bottle.response.set_header('Pragma', 'no-cache')
    bottle.response.set_header('Expires', 0)
    return bottle.static_file(file, root=root_path)



def start_server(urls):
    from webview import _debug
    global address, root_path, running, js_api_endpoint

    local_urls = [u for u in urls if is_local_url(u)]
    common_path = os.path.dirname(os.path.commonpath(local_urls)) if len(local_urls) > 0 else None
    root_path = abspath(common_path) if common_path is not None else None

    port = _get_random_port()
    t = threading.Thread(target=lambda: bottle.run(port=port, quiet=not _debug), daemon=True)
    t.start()

    running = True
    address = f'http://127.0.0.1:{port}/'
    js_api_endpoint = f'{address}js_api/{uid}'

    return address, common_path


