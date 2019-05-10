import webview
from time import sleep

"""
This example demonstrates how to retrieve a DOM element
"""


def get_element(window):
    heading = window.get_element('#heading')
    content = window.get_element('.content')


if __name__ == '__main__':
    html = """
      <html>
        <body>
          <h1 id="heading">Heading</h1>
          <div class="contnet">Content</div>
        </body>
      </html>
    """
    window = webview.create_window('Get element example', html=html)
    webview.start(get_element, window, debug=True)
