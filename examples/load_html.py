import webview
import threading

"""
This example demonstrates how to load HTML in a web view window
"""

def load_html():
    webview.load_html("<h1>This is dynamically loaded HTML</h1>")
    webview.evaluate_js('alert("w00t")')

if __name__ == '__main__':
    t = threading.Thread(target=load_html)
    t.start()

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Simple browser", width=800, height=600, resizable=True)

