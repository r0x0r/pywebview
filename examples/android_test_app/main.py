import logging
import random

from bottle import Bottle, static_file

import webview
from webview.util import get_app_root

logger = logging.getLogger('pywebview')

app = Bottle()


@app.route('/')
def index():
    resp = static_file('index.html', root=get_app_root())
    resp.set_cookie('serverCookie', 'test', httponly=True, secure=True, samesite='Strict')
    return resp


@app.route('/<filename:path>')
def static_files(filename):
    resp = static_file(filename, root=get_app_root())

    if filename.endswith('index.html'):
        logger.debug(f'Serving {filename} with serverCookie set')
        resp.set_cookie('serverCookie', 'test', httponly=True)

    return resp


class TestAPI:
    def getRandomNumber(self):
        return random.randint(0, 100)

    def sayHelloTo(self, name):
        return {'message': f'Hello {name}!'}

    def error(self):
        raise Exception('This is a Python exception')

    def getInteger(self):
        return 420

    def getString(self):
        return 'This is a string from Python'

    def getFloat(self):
        return 4.20

    def getList(self):
        return [1, 2, 3, 4, 5]

    def getNone(self):
        return None

    def getDict(self):
        return {'key1': 'value1', 'key2': 'value2'}


class Api:
    def eval(self, code):
        """Evaluate Python code in the context of this module."""
        try:
            result = eval(code)
            return result
        except Exception as e:
            logger.error(f'Error evaluating Python code: {code}\n{e}')
            return None

    def get_size(self):
        return self._window.height, self._window.width

    def evaluate_js(self, code):
        result = self._window.evaluate_js(code)
        return result

    def run_js(self, code):
        return self._window.run_js(code)

    def get_cookies(self):
        cookies = self._window.get_cookies()
        logger.debug(f'Cookies: {cookies}')
        return [cookie.output() for cookie in cookies]

    def clear_cookies(self):
        self._window.clear_cookies()

    _window = None
    _dom = None
    test1 = TestAPI()
    test2 = TestAPI()


def create_state(state):
    state.number = 0
    state.message = 'test'
    state.dict = {'key': 'value'}
    state.list = [1, 2, 3]
    state.nested = {
        'a': 1,
        'b': [1, 2, 3],
    }


events = {}


def set_event(name, value):
    events[name] = value


if __name__ == '__main__':
    api = Api()
    window = webview.create_window('Android test suite', app, js_api=api, text_select=True)
    create_state(window.state)

    # Window events
    window.events.loaded += lambda: set_event('loaded', True)
    window.events.before_load += lambda: set_event('before_load', True)
    window.events.before_show += lambda: set_event('before_show', True)
    window.events.shown += lambda: set_event('shown', True)
    window.events.request_sent += lambda request: set_event('request_sent', request.__dict__)
    window.events.response_received += lambda response: set_event(
        'response_received', response.__dict__
    )

    api._window = window
    api._dom = window.dom
    webview.start(ssl=True, private_mode=False)
