import webview


class TestAPI:
    def getRandomNumber(self):
        import random
        return random.randint(0, 100)

    def sayHelloTo(self, name):
        return {'message': f'Hello {name}!'}

    def error(self):
        raise Exception('This is a Python exception')


class Api:
    def eval(self, code):
        return eval(code)

    test1 = TestAPI()
    test2 = TestAPI()



def create_state():
    return {
        'number': 0,
        'message': 'test',
        'dict': {'key': 'value'},
        'list': [1, 2, 3],
        'nested': {
            'a': 1,
            'b': [1, 2, 3],
            'c': {'d': 4}
        }
    }


if __name__ == '__main__':
    api = Api()
    window = webview.create_window('Android test suite', './test_runner.html', js_api=api)
    window.state = create_state()
    #api.window = window
    webview.start(debug=True)