import webview

"""
This example demonstrates evaluating async JavaScript
"""

def callback(result):
    print(result)

def evaluate_js_async(window):
    window.evaluate_js(
        """
        new Promise((resolve, reject) => {
            setTimeout(() => {
                resolve('Whaddup!');
            }, 300);
        });
        """, callback)


if __name__ == '__main__':
    window = webview.create_window('Run custom JavaScript', html='<html><body></body></html>')
    webview.start(evaluate_js_async, window, debug=True)
