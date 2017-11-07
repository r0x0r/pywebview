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
        window.pywebview = {
            api: {}
        }
        var test = function(funcList) {
            for (var i = 0; i < funcList.length; i++) {
                pywebview.api[funcList[i]] = function (params) {
                    alert(params)
                    //return window.external.Invoke(funcList[i], params)
                }
            }
        }

        test(['test', 'test2'])
        pywebview.api.test('1')

        """
        )
    )


if __name__ == '__main__':
    t = threading.Thread(target=evaluate_js)
    t.start()

    webview.create_window('Run custom JavaScript', 'http://www.flowrl.com')

