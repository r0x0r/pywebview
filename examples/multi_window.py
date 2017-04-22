import webview
import threading

"""
This example demonstrates multi-window capabilities of pywebview.
Currently works only on Mac.
"""

def load_html():
    webview.load_html(
            """
            <!doctype html>
            <html>
            <body>
                <h1>Create multiple windows for your application!</h1>
                <p>Using the techniques you already know!</p>
                <hr>
                <h4>Using HTML anchor with target _blank</h4>
                <a target="_blank" href="http://www.github.com/r0x0r/pywebview">
                    Pywebview Homepage
                </a>
                <br>
                <h4>Using JavaScript window.open() method</h4>
                <button onclick="window.open('https://www.w3schools.com/jsref/met_win_open.asp', '_blank')">Learn this technique</button>
            </body>
            </html>
            """
            )


if __name__ == '__main__':
    t = threading.Thread(target=load_html)
    t.start()

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Smart browser", width=800, height=600, resizable=True)

