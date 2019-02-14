# Javascript evaluation

Evaluate Javascript from Python code.

``` import webview
import threading


def evaluate_js():
    result = webview.evaluate_js(
        r"""
        var h1 = document.createElement('h1')
        var text = document.createTextNode('Hello pywebview')
        h1.appendChild(text)
        document.body.appendChild(h1)

        document.body.style.backgroundColor = '#212121'
        document.body.style.color = '#f2f2f2'

        // Return user agent
        'User agent:\n' + navigator.userAgent;
        """
    )

    print(result)


if __name__ == '__main__':
    t = threading.Thread(target=evaluate_js)
    t.start()

    webview.create_window('Run custom JavaScript')
```