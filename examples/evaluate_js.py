import webview
import threading

"""
This example demonstrates evaluating JavaScript in a webpage.
"""

def evaluate_js():
    import time
    time.sleep(5)

    # Change document background color and print document title
    print(webview.evaluate_js(
        """
        /* Turn night mode ON */
        document.body.style.backgroundColor = '#212121';
        document.body.style.color = '#f2f2f2';

        /* Return document title */
        document.title;
        """
        )
    )


if __name__ == '__main__':
    t = threading.Thread(target=evaluate_js)
    t.start()

    webview.create_window('Run custom JavaScript', 'http://www.flowrl.com')

