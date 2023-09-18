"""This example demonstrates how to manipulate DOM in Python."""

import random
import webview

rectangles = []

def random_color():
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)

    return f'rgb({red}, {green}, {blue})'

def create_rectangle(window, container):
    color = random_color()
    rectangle = window.dom.create_element(f'<div class="rectangle" style="background-color: {color};"></div>', container)
    rectangles.append(rectangle)


def remove_rectangle(_):
    if len(rectangles) > 0:
        rectangles.pop().remove()


def change_color(rectangle):
    rectangle.style = { 'background-color': random_color() }


def bind(window):
    container = window.dom.get_element('.container')
    rectangle = window.dom.get_element('#rectangle')

    toggle_button = window.dom.get_element('#toggle-button')
    remove_button = window.dom.get_element('#remove-button')
    add_button = window.dom.get_element('#add-button')
    color_button = window.dom.get_element('#color-button')

    toggle_button.events.click += lambda e: rectangle.toggle()
    remove_button.events.click += remove_rectangle
    add_button.events.click += lambda e: create_rectangle(window, container)
    color_button.events.click += lambda e: change_color(rectangle)



if __name__ == '__main__':
    window = webview.create_window(
        'DOM Manipulations Example', html='''
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
                        margin: 0.5rem;
                    }

                    .container {
                        display: flex;
                        flex-wrap: wrap;
                    }
                </style>
                </head>
                <body>
                    <button id="toggle-button">Toggle rectangle</button>
                    <button id="color-button">Change color</button>
                    <button id="remove-button">Remove rectangle</button>
                    <button id="add-button">Add rectangle</button>
                    <div class="container">
                        <div id="rectangle" class="rectangle" style="background-color: red;">

                        </div>
                    </div>
                </body>
            </html>
        '''
    )
    webview.start(bind, window, debug=True)
