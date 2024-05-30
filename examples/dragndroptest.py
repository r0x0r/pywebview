import webview
from webview.dom import DOMEventHandler

import datetime

def on_drag(e):
    print(f"on_drag {datetime.datetime.now()}")
    pass

def on_drop(e):
    print(f"on_drop {datetime.datetime.now()}")
    files = e['dataTransfer']['files']
    if len(files) == 0:
        return
    print(f'Event: {e["type"]}. Dropped files:')
    for file in files:
        print(file.get('pywebviewFullPath'))

def bind(window):
    #window.dom.document.events.dragenter += DOMEventHandler(on_drag, True, True)
    #window.dom.document.events.dragstart += DOMEventHandler(on_drag, True, True)
    #window.dom.document.events.dragover += DOMEventHandler(on_drag, True, True)
    window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)

if __name__ == '__main__':
    window = webview.create_window(
        'Drag & drop example', 'https://google.com'
    )
    webview.start(bind, window)
