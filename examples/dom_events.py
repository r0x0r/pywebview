"""This example demonstrates how to expose Python functions to the Javascript domain."""

import webview
from webview.dom import DOMEventHandler

window = None

def click_handler(e):
    print(e)


def input_handler(e):
    print(e['target']['value'])


def remove_handlers(scroll_event, click_event, input_event):
    scroll_event -= scroll_handler
    click_event -= click_handler
    input_event -= input_handler


def scroll_handler(e):
    scroll_top = window.dom.window.node['scrollY']
    print(f'Scroll position {scroll_top}')


def link_handler(e):
    print(f"Link target is {e['target']['href']}")


def bind(window):
    window.dom.document.events.scroll += DOMEventHandler(scroll_handler, debounce=100)

    button = window.dom.get_element('#button')
    button.events.click += click_handler

    input = window.dom.get_element('#input')
    input.events.input += input_handler

    remove_events = window.dom.get_element('#remove')
    remove_events.on('click', lambda e: remove_handlers(window.dom.document.events.scroll, button.events.click, input.events.input))

    link = window.dom.get_element('#link')
    link.events.click += DOMEventHandler(link_handler, prevent_default=True)


if __name__ == '__main__':
    window = webview.create_window(
        'DOM Event Example', html='''
            <html>
                <head>
                <style>
                    button {
                        font-size: 100%;
                        padding: 0.5rem;
                        margin: 0.3rem;
                        text-transform: uppercase;
                    }
                </style>
                </head>
                <body style="height: 200vh;">
                    <div>
                        <input id="input" placeholder="Enter text">
                        <button id="button">Click me</button>
                        <a id="link" href="https://pywebview.flowrl.com">Click me</a>
                    </div>
                    <button id="remove" style="margin-top: 1rem;">Remove events</button>
                </body>
            </html>
        '''
    )
    webview.start(bind, window)
