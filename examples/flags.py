import webview

"""
Use application flags to modify default behaviour of pywebview
"""


html = """
  <html>
    <head></head>
    <body>
      <h2></h2>
      <p><a href='https://pywebview.flowrl.com' target='_blank'>target='_blank' link</a> will be opened in the current window.</p>
    </body>
  </html>
"""


if __name__ == '__main__':
    webview.FLAGS['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
    webview.FLAGS['OPEN_DEVTOOLS_IN_DEBUG'] = False

    window = webview.create_window('Application flags', html=html)
    webview.start(debug=True)
