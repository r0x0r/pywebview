"""Subscribe and unsubscribe to pywebview events."""

import webview


def on_request(window, request):
    request.headers['test'] = 'test'


def on_response(window, response):
    return
    print(response)


if __name__ == '__main__':
    window = webview.create_window(
        'Simple browser', 'https://www.whatismybrowser.com/detect/what-http-headers-is-my-browser-sending/'
    )

    window.events.request_sent += on_request
    window.events.response_received += on_response

    webview.start(private_mode=False)
