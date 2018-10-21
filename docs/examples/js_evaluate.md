# Javascript evaluation

Evaluate Javascript from Python code.

``` python
import webview
import threading


def evaluate_js():
    # Change document background color and print document title
    print(webview.evaluate_js(
        """
        // Turn dark mode on
        document.body.style.backgroundColor = '#212121';
        document.body.style.color = '#f2f2f2';

        // Return document title
        document.title;
        """
    )
    )


if __name__ == '__main__':
    t = threading.Thread(target=evaluate_js)
    t.start()

    webview.create_window('Run custom JavaScript', 'https://pywebview.flowrl.com/hello')
```