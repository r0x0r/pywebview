"""This example demonstrates how to manipulate DOM in Python."""

import random
import webview

rectangles = []

def random_color():
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)

    return f'rgb({red}, {green}, {blue})'

def bind(window):
    def create_rectangle(_):
        color = random_color()
        rectangle = window.dom.create_element(f'<div class="rectangle" style="background-color: {color};"></div>', container)
        rectangles.append(rectangle)

        disabled = None if len(rectangles) > 0 else True
        remove_button.attributes = { 'disabled': disabled }
        empty_button.attributes = { 'disabled': disabled }

    def remove_rectangle(_):
        if len(rectangles) > 0:
            rectangles.pop().remove()

        disabled = None if len(rectangles) > 0 else True
        remove_button.attributes = { 'disabled': disabled }
        empty_button.attributes = { 'disabled': disabled }

    def empty_container(_):
        container.empty()
        rectangles.clear()

        remove_button.attributes = { 'disabled': True }
        empty_button.attributes = { 'disabled': True }

    def change_color(_):
        circle.style = { 'background-color': random_color() }

    def toggle_class(_):
        circle.toggle_class('circle')

    container = window.dom.get_element('#rectangles')
    circle = window.dom.get_element('#circle')

    toggle_button = window.dom.get_element('#toggle-button')
    toggle_class_button = window.dom.get_element('#toggle-class-button')
    remove_button = window.dom.get_element('#remove-button')
    empty_button = window.dom.get_element('#empty-button')
    add_button = window.dom.get_element('#add-button')
    color_button = window.dom.get_element('#color-button')

    toggle_button.events.click += lambda e: circle.toggle()
    toggle_class_button.events.click += toggle_class
    remove_button.events.click += remove_rectangle
    empty_button.events.click += empty_container
    add_button.events.click += create_rectangle
    color_button.events.click += change_color


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
                        border-radius: 5px;
                    }

                    .circle {
                        border-radius: 50px;
                    }

                    .container {
                        display: flex;
                        flex-wrap: wrap;
                    }
                </style>
                </head>
                <body>
                    <button id="toggle-button">Toggle circle</button>
                    <button id="toggle-class-button">Toggle class</button>
                    <button id="color-button">Change color</button>
                    <button id="add-button">Add rectangle</button>
                    <button id="remove-button" disabled>Remove rectangle</button>
                    <button id="empty-button" disabled>Remove all</button>
                    <div>
                        <div id="circle" class="rectangle circle" style="background-color: red;"></div>
                        <div id="rectangles" class="container"></div>
                    </div>
                </body>
            </html>
        '''
    )
    webview.start(bind, window, debug=True)
