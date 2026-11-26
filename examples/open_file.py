"""
Handle files and URLs opened with the application, e.g. by double-clicking a document in a file
manager.

webview.events.opened is fired with a dictionary of the files and URLs to open. On macOS it is
fired for files opened at launch and while the application is running. On Windows and Linux, the
operating system starts the application with the file path on the command line, which fires the
event once the window is shown. With single_instance=True, a later launch hands its command line
to the running instance instead of opening another window. Run `python open_file.py`, then
`python open_file.py open_file.py` in another terminal.

The application must declare the file types it opens,
see https://pywebview.flowrl.com/guide/freezing.html#opening-files
"""

import json

import webview


def on_opened(request):
    window = webview.windows[0]

    for item in request['files'] + request['urls']:
        window.evaluate_js(f'showFile({json.dumps(item)})')


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
    webview.create_window('Open file', html=html)
    webview.events.opened += on_opened
    webview.start(single_instance=True)
