"""Subscribe and unsubscribe to pywebview events."""

from bottle import Bottle, request, response

import webview


def on_request(window, request):
    print('Request sent: ' + request.url)

    if request.url.endswith('/favicon.ico'):
        return False  # cancel the request

    request.headers['pywebview'] = 'header'


def on_response(window, response):
    print('Response received: ' + response.url)


app = Bottle()


@app.route('/')
def display_headers():
    headers = dict(request.headers)
    # The image and the fetch request fire the events too, except request_sent on macOS
    return '<br>'.join(f'{key}: {value}' for key, value in headers.items()) + (
        '<br><img src="/image.svg"><script>fetch("/data")</script>'
    )


@app.route('/image.svg')
def image():
    response.content_type = 'image/svg+xml'
    return '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>'


@app.route('/data')
def data():
    return {'message': 'Hello from fetch'}


if __name__ == '__main__':
    window = webview.create_window('Headers', app)

    window.events.request_sent += on_request
    window.events.response_received += on_response

    webview.start(debug=True)
