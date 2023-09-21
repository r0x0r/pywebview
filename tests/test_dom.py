import pytest

import webview
from time import sleep
from .util import run_test


@pytest.fixture
def window():
    return webview.create_window('DOM test', html='''
        <html>
            <body>
                <div id="container">
                    <div id="child1" class="test" data-id="blz" tabindex="3">DUDE</div>
                    <div id="child2" class="test"></div>
                    <div id="child3" class="test" style="display: none; background-color: rgb(255, 0, 0)" tabindex="2"></div>
                </div>
                <div id="container2">
                    <input type="text" value="pizdec" id="input"/>
                    <button id="button">Click me</button>
                </div>
            </body>
        </html>
    ''')


def test_element(window):
    run_test(webview, window, element_test)


def test_classes(window):
    run_test(webview, window, classes_test)


def test_style(window):
    run_test(webview, window, style_test)


def test_traversal(window):
    run_test(webview, window, traversal_test)


def test_visibility(window):
    run_test(webview, window, visibility_test)

def test_focus(window):
    run_test(webview, window, focus_test)

def test_manipulation(window):
    run_test(webview, window, manipulation_test)


def test_events(window):
    run_test(webview, window, events_test)


def element_test(window):
    child1 = window.dom.get_element('#child1')

    assert child1.id == 'child1'
    assert child1.tag == 'div'
    assert child1.attributes == {'class': 'test', 'id': 'child1', 'data-id': 'blz', 'tabindex': '3'}
    assert child1.tabindex == 3
    assert child1.text == 'DUDE'

    child1.text = 'WOW'
    assert child1.text == 'WOW'

    child1.tabindex = 10
    assert child1.tabindex == 10

    input = window.dom.get_element('#input')
    assert input.value == 'pizdec'
    input.value = 'tisok'
    assert input.value == 'tisok'




def classes_test(window):
    child1 = window.dom.get_element('#child1')
    assert child1.classes == ['test']

    child1.add_class('test2')
    assert child1.classes == ['test', 'test2']

    child1.toggle_class('test')
    assert child1.classes == ['test2']

    child1.toggle_class('test')
    assert child1.classes == ['test2', 'test']

    child1.classes = ['woah']
    assert child1.classes == ['woah']


def style_test(window):
    child3 = window.dom.get_element('#child3')
    assert child3.style['display'] == 'none'
    assert child3.style['background-color'] == 'rgb(255, 0, 0)'

    child3.style = { 'display': 'block' }
    child3.style = { 'background-color': 'rgb(0, 0, 255)' }
    assert child3.style['display'] == 'block'
    assert child3.style['background-color'] == 'rgb(0, 0, 255)'


def visibility_test(window):
    child3 = window.dom.get_element('#child3')
    assert child3.visible == False

    child3.show()
    assert child3.visible == True

    child3.hide()
    assert child3.visible == False

    child3.toggle()
    assert child3.visible == True

    child3.toggle()
    assert child3.visible == False


def focus_test(window):
    input = window.dom.get_element('#input')
    assert input.focused == False

    input.focus()
    assert input.focused == True

    input.blur()
    assert input.focused == False


def traversal_test(window):
    child2 = window.dom.get_element('#child2')


    assert child2.parent.id == 'container'
    assert child2.next.id == 'child3'
    assert child2.previous.id == 'child1'

    children = window.dom.get_element('#container').children

    assert len(children) == 3
    assert children[0].id == 'child1'
    assert children[1].id == 'child2'
    assert children[2].id == 'child3'


def manipulation_test(window):
    container = window.dom.get_element('#container')
    assert len(container.children) == 3

    container.empty()
    assert container.children == []

    container.append('<div id="child1"></div>')
    assert len(container.children) == 1
    assert container.children[0].id == 'child1'

    child2 = window.dom.create_element('<div id="child2"></div>', container)
    assert len(container.children) == 2
    assert container.children[1].id == 'child2'
    assert child2.parent.id == 'container'
    assert child2.id == 'child2'

    container.children[0].remove()
    assert len(container.children) == 1
    assert container.children[0].id == 'child2'


def events_test(window):
    def click_handler(event):
        nonlocal button_value
        assert event['target']['id'] == 'button'
        button_value = True

    button_value = False
    button = window.dom.get_element('#button')
    button.events.click += click_handler

    window.evaluate_js('document.getElementById("button").click()')
    assert button_value == True

    button.events.click -= click_handler
    button_value = False
    window.evaluate_js('document.getElementById("button").click()')
    sleep(0.1)
    assert button_value == False
    assert window.evaluate_js('Object.keys(pywebview._eventHandlers).length === 0') == True