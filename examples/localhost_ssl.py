import webview

if __name__ == '__main__':
  webview.create_window('Local SSL Test', 'assets/index.html')
  gui = 'qt' # or 'gtk'
  webview.start(gui=gui, ssl=True)

