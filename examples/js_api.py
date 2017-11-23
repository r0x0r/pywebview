import webview
import threading
import time

'''
This example demonstrates how to create a pywebview api without using a web server
'''

class Api:
    def init(self, params):
        return '{message: "initialization complete"}'

    def do_stuff(self, params):
        return '{message: "done stuff"}'

    def do_heavy_stuff(self, params):
        time.sleep(5)
        return '{message: "done heavy stuff"}'



def create_app():
    webview.load_html('<h1>Serverless application</h1>')
    api = Api()
    webview.set_js_api(api)
    webview.evaluate_js('''
        window.pywebview.api.init()
            .then(function(msg) {
                alert(JSON.stringify(msg))
            })

        window.pywebview.api.do_heavy_stuff()
            .then(function(msg) {
                alert(JSON.stringify(msg))
            })
    ''')


if __name__ == '__main__':
    t = threading.Thread(target=create_app)
    t.start()

    webview.create_window('API example', debug=True)

