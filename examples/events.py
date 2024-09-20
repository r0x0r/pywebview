"""Subscribe and unsubscribe to pywebview events."""

import webview
from webview.models import Request, Response


def on_closed():
    print('pywebview window is closed')


def on_closing():
    print('pywebview window is closing')


def on_shown():
    print('pywebview window shown')


def on_minimized():
    print('pywebview window minimized')


def on_restored():
    print('pywebview window restored')


def on_maximized():
    print('pywebview window maximized')


def on_resized(width, height):
    print(
        'pywebview window is resized. new dimensions are {width} x {height}'.format(
            width=width, height=height
        )
    )


# you can supply optional window argument to access the window object event was triggered on
def on_loaded(window):
    print('DOM is ready')

    # unsubscribe event listener
    window.events.loaded -= on_loaded
    window.load_url('https://pywebview.flowrl.com/hello')


def on_moved(x, y):
    print('pywebview window is moved. new coordinates are x: {x}, y: {y}'.format(x=x, y=y))

def on_request_sent(request: Request):
    try:
        method = request.method
        uri = request.url
        request_headers = request.headers
        data_stream = request.content_stream
        data = data_stream.decode('utf-8') if data_stream else None
        # Add custom header
        request.headers['x-Token'] = '123123231'
        # Remove header
        request.headers['Content-Security-Policy'] = None
        # if you want have the response, you can set the request.response
    except Exception as e:
        print(e)


def on_response_received(response: Response):
    content_stram = response.content_stram
    content = ''
    if content_stram:
        content = content_stram.decode('utf-8')
    uri = response.url
    print(uri, content)


if __name__ == '__main__':
    window = webview.create_window(
        'Simple browser', 'https://pywebview.flowrl.com/', confirm_close=True
    )

    window.events.closed += on_closed
    window.events.closing += on_closing
    window.events.shown += on_shown
    window.events.loaded += on_loaded
    window.events.minimized += on_minimized
    window.events.maximized += on_maximized
    window.events.restored += on_restored
    window.events.resized += on_resized
    window.events.moved += on_moved

    window.events.request_sent += on_request_sent
    window.events.response_received += on_response_received

    webview.start()
