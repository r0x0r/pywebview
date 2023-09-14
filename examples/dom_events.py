"""This example demonstrates how to expose Python functions to the Javascript domain."""

import webview


def click_handler(e):
    print(e)


def input_handler(e):
    print(e['target']['value'])


def remove_handlers(document, button, input):
    document.off('scroll', scroll_handler)
    button.off('click', click_handler)
    input.off('input', input_handler)


def scroll_handler(window):
    scroll_top = window.dom.window.node['scrollY']
    print(f'Scroll position {scroll_top}')


def bind(window):
    window.dom.document.on('scroll', lambda e: scroll_handler(window))

    button = window.get_elements('#button')[0]
    button.on('click', click_handler)

    input = window.get_elements('#input')[0]
    input.on('input', input_handler)

    remove_events = window.get_elements('#remove')[0]
    remove_events.on('click', lambda e: remove_handlers(window.dom.document, button, input))


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
                    </div>
                    <button id="remove" style="margin-top: 1rem;">Remove events</button>
                </body>
            </html>
        '''
    )
    webview.start(bind, window, debug=True)
