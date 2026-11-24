"""
Handle files opened with the application, e.g. by double-clicking a document in a file manager.

window.events.file_opened is fired with a list of paths. On macOS it is fired for files opened
at launch and while the application is running. On Windows and Linux, the operating system
starts the application with the file path on the command line, which fires the event once the
window is shown. Try `python open_file.py open_file.py`.

The application must declare the file types it opens,
see https://pywebview.flowrl.com/guide/freezing.html#opening-files
"""

import json

import webview


def on_file_opened(window, paths):
    for path in paths:
        window.evaluate_js(f'showFile({json.dumps(path)})')


html = """
<h1>Opened files</h1>
<ul id="files"></ul>
<script>
  function showFile(path) {
    const item = document.createElement('li')
    item.textContent = path
    document.getElementById('files').appendChild(item)
  }
</script>
"""

if __name__ == '__main__':
    window = webview.create_window('Open file', html=html)
    window.events.file_opened += on_file_opened
    webview.start()
