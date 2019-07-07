import webview
import threading

"""
This example demonstrates a difference between different link types
"""


html = """
  <html>
    <head></head>
    <body>
      <h2>Links</h2>

      <p><a href='https://pywebview.flowrl.com'>Regular links</a> are opened in the application window.</p>
      <p><a href='https://pywebview.flowrl.com' target='_blank'>target='_blank' links</a> are opened in an external browser.</p>

    </body>
  </html>
"""


if __name__ == '__main__':
    window = webview.create_window('Link types', html=html)
    webview.start()
