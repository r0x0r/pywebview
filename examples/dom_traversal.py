"""This example demonstrates how to traverse DOM in Python."""

import webview


def bind(window):
    container = window.dom.get_element('#container')
    container_button = window.dom.get_element('#container-button')
    blue_rectangle = window.dom.get_element('#blue-rectangle')
    blue_parent_button = window.dom.get_element('#blue-parent-button')
    blue_next_button = window.dom.get_element('#blue-next-button')
    blue_previous_button = window.dom.get_element('#blue-previous-button')

    container_button.events.click += lambda e: print(container.children)
    blue_parent_button.events.click += lambda e: print(blue_rectangle.parent)
    blue_next_button.events.click += lambda e: print(blue_rectangle.next)
    blue_previous_button.events.click += lambda e: print(blue_rectangle.previous)


if __name__ == '__main__':
    window = webview.create_window(
        'DOM Manipulations Example',
        html="""
            <html>
                <head>
                <style>
                    button {
                        font-size: 100%;
                        padding: 0.5rem;
                        margin: 0.3rem;
                        text-transform: uppercase;
                    }

                    .rectangle {
                        width: 100px;
                        height: 100px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        color: white;
                        margin-right: 5px;
                    }
                </style>
                </head>
                <body>
                    <h1>Container</h1>
                    <div id="container" style="border: 1px #eee solid; display: flex; padding: 10px 0;">
                        <div id="red-rectangle" class="rectangle" style="background-color: red;">RED</div>
                        <div id="blue-rectangle" class="rectangle" style="background-color: blue;">BLUE</div>
                        <div id="green-rectangle" class="rectangle" style="background-color: green;">GREEN</div>
                    </div>
                    <button id="container-button">Get container's children</button>
                    <button id="blue-parent-button">Get blue's parent</button>
                    <button id="blue-next-button">Get blue's next element</button>
                    <button id="blue-previous-button">Get blue's previous element</button>
                </body>
            </html>
        """,
    )
    webview.start(bind, window)
