"""Subscribe and unsubscribe to pywebview events."""

import webview


def on_request(window, headers):
    print(f'Request headers: {headers}')


def on_response(window, headers):
    print(f'Response headers: {headers}')


if __name__ == '__main__':
    window = webview.create_window(
        'Simple browser', 'https://pywebview.flowrl.com/', confirm_close=True
    )

    window.events.request_sent += on_request
    window.events.response_received += on_response

    webview.start()
