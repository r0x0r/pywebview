"""Subscribe and unsubscribe to pywebview events."""

import webview
import httpx


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


def on_request_sent(args):
    request = args.get('request')
    method = request.get('method')
    uri = request.get('uri')
    request_headers = request.get('headers')
    data_stream = request.get('data_stream')
    data = data_stream.decode('utf-8') if data_stream else None
    # Add proxy
    proxies = {'http://': 'http://127.0.0.1:10809', 'https://': 'http://127.0.0.1:10809'}

    with httpx.Client(proxies=proxies, verify=False) as client:
        res: httpx.Response = client.request(
            method, uri, headers=request_headers, data=data)
    # print('on_request_sent', uri, res.status_code, res.headers)
    # Add custom headers
    res_headers = {'X-Token': 'test'}
    for header_k, headers_v in res.headers.items():
        # remove headers
        if header_k.lower() in ['content-security-policy', 'etag']:
            continue
        res_headers[header_k] = headers_v
    response = {
        'status_code': res.status_code,
        'headers': res_headers,
        'content': res.content,
        'reason_phrase': res.reason_phrase
    }
    args['response'] = response


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

    webview.start()
