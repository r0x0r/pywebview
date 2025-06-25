import webview
import logging

try:
    from jnius import JavaException
except ImportError:
    JavaException = Exception
    detach = lambda: None

logger = logging.getLogger('pywebview')


class TestAPI:
    def getRandomNumber(self):
        import random
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
        """ Evauate Python code in the context of this module. """
        try:
            result = eval(code)
            return result
        except (JavaException, Exception) as e:
            logger.error(f'Error evaluating code: {code}\n{e}')
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

events = {

}

def set_event(name, value):
    events[name] = value


if __name__ == '__main__':
    api = Api()
    window = webview.create_window('Android test suite', './index.html', js_api=api, text_select=True)
    create_state(window.state)

    # Window events
    window.events.loaded += lambda: set_event('loaded', True)
    window.events.before_load += lambda: set_event('before_load', True)
    window.events.before_show += lambda: set_event('before_show', True)
    window.events.shown += lambda: set_event('shown', True)
    window.events.request_sent += lambda request: set_event('request_sent', request.__dict__)
    window.events.response_received += lambda response: set_event('response_received', response.__dict__)

    api._window = window
    api._dom = window.dom
    webview.start(debug=True)