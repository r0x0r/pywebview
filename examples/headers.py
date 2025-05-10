"""Subscribe and unsubscribe to pywebview events."""

import webview


def on_request(window, request):
    request.headers['pywebview'] = 'header'


def on_response(window, response):
    print(response)


if __name__ == '__main__':
    window = webview.create_window(
        'Headers', 'https://httpbin.org/headers'
    )

    window.events.request_sent += on_request
    window.events.response_received += on_response

    webview.start(private_mode=False)
