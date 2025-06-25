"""Get DOM elements using selectors."""

import webview


def get_elements(window):
    heading = window.dom.get_elements('#heading')
    content = window.dom.get_elements('.content')
    print('Heading:\n %s ' % heading[0].node['outerHTML'])
    print('Content 1:\n %s ' % content[0].node['outerHTML'])
    print('Content 2:\n %s ' % content[1].node['outerHTML'])


if __name__ == '__main__':
    html = """
      <html>
        <body>
          <h1 id="heading">Heading</h1>
          <div class="content">Content 1</div>
          <div class="content">Content 2</div>
        </body>
      </html>
    """
    window = webview.create_window('Get elements example', html=html)
    webview.start(get_elements, window)
