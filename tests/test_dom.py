from time import sleep

import pytest

import webview

from .util import run_test


@pytest.fixture
def window():
    return webview.create_window(
        'DOM test',
        html="""
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
    """,
    )


def test_element(window):
    run_test(webview, window, element_test)


def test_classes(window):
    run_test(webview, window, classes_test)


def test_attributes(window):
    run_test(webview, window, attributes_test)


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


def test_manipulation_modes(window):
    run_test(webview, window, manipulation_mode_test)


def test_events(window):
    run_test(webview, window, events_test)


def test_special_char_attributes(window):
    run_test(webview, window, special_char_attributes_test)


def element_test(window):
    child1 = window.dom.get_element('#child1')

    assert child1.id == 'child1'
    assert child1.tag == 'div'
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
    assert list(child1.classes) == ['test']

    child1.classes.append('test2')
    assert list(child1.classes) == ['test', 'test2']

    child1.classes.toggle('test')
    assert list(child1.classes) == ['test2']

    child1.classes.toggle('test')
    assert list(child1.classes) == ['test2', 'test']

    child1.classes = ['woah']
    assert list(child1.classes) == ['woah']

    child1.classes.clear()
    assert len(child1.classes) == 0


def attributes_test(window):
    child1 = window.dom.get_element('#child1')

    assert dict(child1.attributes) == {
        'class': 'test',
        'id': 'child1',
        'data-id': 'blz',
        'tabindex': '3',
    }

    assert child1.attributes['class'] == 'test'
    assert set(child1.attributes.keys()) == {'class', 'id', 'data-id', 'tabindex'}
    assert set(child1.attributes.values()) == {'test', 'child1', 'blz', '3'}
    assert set(child1.attributes.items()) == {
        ('class', 'test'),
        ('id', 'child1'),
        ('data-id', 'blz'),
        ('tabindex', '3'),
    }
    assert child1.attributes.get('class') == 'test'
    assert child1.attributes.get('class2') == None
    assert child1.attributes['class2'] == None

    del child1.attributes['class']
    assert dict(child1.attributes) == {'id': 'child1', 'data-id': 'blz', 'tabindex': '3'}

    child1.attributes['data-test'] = 'test2'
    assert dict(child1.attributes) == {
        'id': 'child1',
        'data-id': 'blz',
        'tabindex': '3',
        'data-test': 'test2',
    }

    child1.attributes = {'data-test': 'test3'}
    assert child1.attributes['data-test'] == 'test3'

    child1.attributes.clear()
    assert dict(child1.attributes) == {}


def style_test(window):
    child3 = window.dom.get_element('#child3')
    assert child3.style['display'] == 'none'
    assert child3.style['background-color'] == 'rgb(255, 0, 0)'

    child3.style['display'] = 'flex'
    child3.style['background-color'] = 'rgb(0, 0, 255)'
    assert child3.style['display'] == 'flex'
    assert child3.style['background-color'] == 'rgb(0, 0, 255)'

    child3.style.clear()
    assert child3.style['display'] == 'block'
    assert child3.style['background-color'] == 'rgba(0, 0, 0, 0)'


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
    container2 = window.dom.get_element('#container2')
    assert len(container.children) == 3

    container.empty()
    assert container.children == []

    container.append('<div id="child1"></div>')
    assert len(container.children) == 1
    assert container.children[0].id == 'child1'

    child2 = window.dom.create_element(
        '<div id="child2" class="child-class">CHILD</div>', container
    )
    assert len(container.children) == 2
    assert container.children[1].id == 'child2'
    assert child2.parent.id == 'container'
    assert child2.id == 'child2'

    child3 = child2.copy(container2)
    assert len(container2.children) == 3
    assert container2.children[2].text == 'CHILD'
    assert list(child3.classes) == ['child-class']
    assert child3.id == ''
    assert child2._node_id != child3._node_id

    child4 = child2.copy()
    child4.parent.id = 'container'
    assert len(container.children) == 3

    child4.move(container2)
    assert len(container.children) == 2
    assert len(container2.children) == 4

    container.children[0].remove()
    assert len(container.children) == 1
    assert container.children[0].id == 'child2'


def manipulation_mode_test(window):
    child1 = window.dom.get_element('#child1')
    child2 = window.dom.get_element('#child2')
    child3 = window.dom.get_element('#child3')
    container2 = window.dom.get_element('#container2')

    child1.move(container2, mode=webview.dom.ManipulationMode.FirstChild)
    assert container2.children[0].id == 'child1'

    child2.move(container2, mode=webview.dom.ManipulationMode.LastChild)
    assert container2.children[-1].id == 'child2'

    child3.move(child1, mode=webview.dom.ManipulationMode.Before)
    assert container2.children[0].id == 'child3'

    child1.move(child2, mode=webview.dom.ManipulationMode.After)
    assert container2.children[-1].id == 'child1'

    child2.move(container2, mode=webview.dom.ManipulationMode.Replace)
    assert window.dom.get_element('#container2') == None
    assert child2.parent.tag == 'body'


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


def special_char_attributes_test(window):
    """Test attributes containing special characters like single quotes and backslashes"""
    child1 = window.dom.get_element('#child1')

    # Test setting and getting attributes with double quotes (should work with JSON)
    child1.attributes['data-double-quote'] = 'value with "double quotes"'
    assert child1.attributes['data-double-quote'] == 'value with "double quotes"'

    # Test setting and getting attributes with backslashes (JSON escapes these)
    child1.attributes['data-backslash'] = 'value with \\backslash'
    assert child1.attributes['data-backslash'] == 'value with \\backslash'

    # Test setting and getting attributes with newlines and tabs
    child1.attributes['data-whitespace'] = 'value with\nnewline and\ttab'
    assert child1.attributes['data-whitespace'] == 'value with\nnewline and\ttab'

    # Test setting and getting attributes with HTML entities
    child1.attributes['data-html'] = 'value with &lt;tags&gt; and &amp; symbols'
    assert child1.attributes['data-html'] == 'value with &lt;tags&gt; and &amp; symbols'

    # Test setting and getting attributes with Unicode characters
    child1.attributes['data-unicode'] = 'value with unicode: ñáéíóú 中文 🚀'
    assert child1.attributes['data-unicode'] == 'value with unicode: ñáéíóú 中文 🚀'

    # Test setting and getting attributes with forward slashes
    child1.attributes['data-slashes'] = 'value/with/forward/slashes'
    assert child1.attributes['data-slashes'] == 'value/with/forward/slashes'

    # Test that all special character attributes are preserved
    special_attrs = {k: v for k, v in child1.attributes.items() if k.startswith('data-')}
    expected_attrs = {
        'data-id': 'blz',  # original attribute
        'data-double-quote': 'value with "double quotes"',
        'data-backslash': 'value with \\backslash',
        'data-whitespace': 'value with\nnewline and\ttab',
        'data-html': 'value with &lt;tags&gt; and &amp; symbols',
        'data-unicode': 'value with unicode: ñáéíóú 中文 🚀',
        'data-slashes': 'value/with/forward/slashes',
    }

    for key, expected_value in expected_attrs.items():
        assert key in special_attrs, f'Attribute {key} not found'
        assert (
            special_attrs[key] == expected_value
        ), f'Attribute {key} value mismatch: expected {expected_value}, got {special_attrs[key]}'

    # Test clearing special character attributes
    for key in [
        'data-double-quote',
        'data-backslash',
        'data-whitespace',
        'data-html',
        'data-unicode',
        'data-slashes',
    ]:
        del child1.attributes[key]
        assert child1.attributes[key] == None
