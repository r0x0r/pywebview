"""This example demonstrates how to expose Python functions to the Javascript domain."""

import webview
from webview.dom import DOMEventHandler


def on_drag(e):
    pass

def on_drop(e):
    files = e['dataTransfer']['files']
    if len(files) == 0:
        return

    print(f'Event: {e["type"]}. Dropped files:')

    for file in files:
        print(file.get('pywebviewFullPath'))


def bind(window):
    window.dom.document.events.dragenter += DOMEventHandler(on_drag, True, True)
    window.dom.document.events.dragstart += DOMEventHandler(on_drag, True, True)
    window.dom.document.events.dragover += DOMEventHandler(on_drag, True, True)
    window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)

if __name__ == '__main__':
    window = webview.create_window(
        'Drag & drop example', html='''
            <html>
                <body style="height: 100vh;"->
                    <h1>Drag files here</h1>
                </body>
            </html>
        '''
    )
    webview.start(bind, window)
