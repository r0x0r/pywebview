import webview
import threading

"""
This example demonstrates how to toggle fullscreen mode programmatically.
"""

<<<<<<< b1bd30429e64d4a865326a8d9142e22eb5e9e501

=======
>>>>>>> Implement toggle_fullscreen functionality
def toggle_fullscreen():
    import time
    time.sleep(5)
    webview.toggle_fullscreen()


if __name__ == '__main__':
    t = threading.Thread(target=toggle_fullscreen)
    t.start()

    webview.create_window("Full-screen window", "http://www.flowrl.com")

