"""Subscribe and unsubscribe to pywebview events."""

import webview


def on_request(window, request):
    request.headers['test'] = 'test'



def on_response(window, response):
    print(response)


if __name__ == '__main__':
    window = webview.create_window(
        'Simple browser', 'https://www.httpdebugger.com/Tools/ViewBrowserHeaders.aspx'
    )

    window.events.request_sent += on_request
    window.events.response_received += on_response

    webview.start(debug=True)
