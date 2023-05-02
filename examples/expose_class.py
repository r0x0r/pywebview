import webview

"""
This example demonstrates how to expose Python functions to the Javascript domain.
"""


class ApiClass:
    def lol():
        print('LOL')

    def wtf():
        print('WTF')

    def echo(arg1, arg2, arg3):
        print(arg1)
        print(arg2)
        print(arg3)


def expose(window):
    window.expose_class(ApiClass)  # expose a function during the runtime

    window.evaluate_js('pywebview.api.ApiClass.lol()')
    window.evaluate_js('pywebview.api.ApiClass.wtf()')
    window.evaluate_js('pywebview.api.ApiClass.echo(1, 2, 3)')


if __name__ == '__main__':
    window = webview.create_window(
        'JS Expose Example', html='<html><head></head><body><h1>JS Expost</body></html>')

    webview.start(expose, window, debug=True)
