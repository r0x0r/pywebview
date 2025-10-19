"""Run Javascript code from Python."""

import webview


def run_js(window):
    result = window.run_js(
        r"""
        var h1 = document.createElement('h1')
        var text = document.createTextNode('Hello pywebview')
        h1.appendChild(text)
        document.body.appendChild(h1)

        function test() {
            return 420
        }

        test()
        """
    )

    print(result)


if __name__ == '__main__':
    window = webview.create_window('Run JavaScript', html='<html><body></body></html>')
    webview.start(run_js, window)
