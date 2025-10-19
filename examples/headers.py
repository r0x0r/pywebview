"""Subscribe and unsubscribe to pywebview events."""

from bottle import Bottle, request

import webview


def on_request(window, request):
    print('Request sent: ' + request.url)
    request.headers['pywebview'] = 'header'


def on_response(window, response):
    print('Response received: ' + response.url)


app = Bottle()


@app.route('/')
def display_headers():
    headers = dict(request.headers)
    return '<br>'.join(f'{key}: {value}' for key, value in headers.items())


if __name__ == '__main__':
    window = webview.create_window('Headers', app)

    window.events.request_sent += on_request
    window.events.response_received += on_response

    webview.start(debug=True)
