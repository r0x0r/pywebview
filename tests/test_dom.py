from time import sleep

import pytest

import webview
from webview.dom import DOMEventHandler

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


def test_manipulation_errors(window):
    run_test(webview, window, manipulation_error_test)


def test_special_char_attributes(window):
    run_test(webview, window, special_char_attributes_test)


def test_query(window):
    run_test(webview, window, query_test)


def test_special_char_properties(window):
    run_test(webview, window, special_char_properties_test)


def test_create_element(window):
    run_test(webview, window, create_element_test)


def test_copy_with_events(window):
    run_test(webview, window, copy_with_events_test)


def test_removed_element(window):
    run_test(webview, window, removed_element_test)


def test_views(window):
    run_test(webview, window, views_test)


def test_event_handler_options(window):
    run_test(webview, window, event_handler_options_test)


def wait_for(condition, timeout=2):
    # DOM event handlers fire asynchronously over the JS bridge
    for _ in range(int(timeout / 0.1)):
        if condition():
            return True
        sleep(0.1)
    return condition()


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

    child1.classes.remove('test2')
    assert list(child1.classes) == ['test']

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
    assert child1.attributes.get('class2') is None
    assert child1.attributes['class2'] is None

    del child1.attributes['class']
    assert dict(child1.attributes) == {'id': 'child1', 'data-id': 'blz', 'tabindex': '3'}

    child1.attributes['data-test'] = 'test2'
    assert dict(child1.attributes) == {
        'id': 'child1',
        'data-id': 'blz',
        'tabindex': '3',
        'data-test': 'test2',
    }

    assert 'data-test' in child1.attributes
    child1.attributes.update({'data-test': None, 'data-new': 'new'})
    assert 'data-test' not in child1.attributes
    assert child1.attributes['data-new'] == 'new'

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

    del child3.style['display']
    assert child3.style['display'] == 'block'

    child3.style = {'display': 'none', 'margin-top': '5px'}
    assert child3.style['display'] == 'none'
    assert child3.style['margin-top'] == '5px'

    child3.style.clear()
    assert child3.style['display'] == 'block'
    assert child3.style['background-color'] == 'rgba(0, 0, 0, 0)'


def visibility_test(window):
    child3 = window.dom.get_element('#child3')
    assert not child3.visible

    child3.show()
    assert child3.visible

    child3.hide()
    assert not child3.visible

    child3.toggle()
    assert child3.visible

    child3.toggle()
    assert not child3.visible


def focus_test(window):
    input = window.dom.get_element('#input')
    assert not input.focused

    input.focus()
    assert input.focused

    input.blur()
    assert not input.focused


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
    assert window.dom.get_element('#container2') is None
    assert child2.parent.tag == 'body'


def manipulation_error_test(window):
    child1 = window.dom.get_element('#child1')

    # move() with a selector that matches nothing cannot resolve a target
    with pytest.raises(webview.errors.WebViewException):
        child1.move('#does-not-exist')

    # copy() with a selector that matches nothing cannot resolve a target
    with pytest.raises(webview.errors.WebViewException):
        child1.copy('#does-not-exist')

    # copy() with no explicit target and no parent (the root <html> element)
    # cannot resolve a target either
    html_element = window.dom.get_element('html')
    with pytest.raises(webview.errors.WebViewException):
        html_element.copy()


def events_test(window):
    def click_handler(event):
        nonlocal button_value
        button_value = event['target']['id']

    def child_click_handler(event):
        nonlocal child_value
        child_value = True

    button_value = False
    child_value = False
    button = window.dom.get_element('#button')
    button.events.click += click_handler
    # a listener registered later on another element must not hijack the first one
    child1 = window.dom.get_element('#child1')
    child1.events.click += child_click_handler

    window.evaluate_js('document.getElementById("button").click()')

    assert wait_for(lambda: button_value)
    assert button_value == 'button'

    child1.events.click -= child_click_handler
    button.events.click -= click_handler
    button_value = False
    window.evaluate_js('document.getElementById("button").click()')
    sleep(0.1)
    assert not button_value
    assert window.evaluate_js('Object.keys(pywebview._eventHandlers).length === 0')

    # each handler fires once per event, and stopImmediatePropagation skips later handlers
    calls = []
    first = DOMEventHandler(lambda e: calls.append('first'), stop_immediate_propagation=True)
    button.events.click += first
    button.events.click += lambda e: calls.append('second')
    window.evaluate_js('document.getElementById("button").click()')
    sleep(0.5)
    assert calls == ['first']

    # the same callback registered twice is called by both listeners, and off removes one
    child_calls = []

    def count(e):
        child_calls.append(1)

    child1.events.click += count
    child1.events.click += count
    window.evaluate_js('document.getElementById("child1").click()')
    sleep(0.5)
    assert len(child_calls) == 2

    child1.events.click -= count
    window.evaluate_js('document.getElementById("child1").click()')
    sleep(0.5)
    assert len(child_calls) == 3

    # handlers added through another wrapper of the same node are called as well
    window.dom.get_element('#child1').events.click += count
    window.evaluate_js('document.getElementById("child1").click()')
    sleep(0.5)
    assert len(child_calls) == 5


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
        assert special_attrs[key] == expected_value, (
            f'Attribute {key} value mismatch: expected {expected_value}, got {special_attrs[key]}'
        )

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
        assert child1.attributes[key] is None


def query_test(window):
    children = window.dom.get_elements('#container .test')
    assert [c.id for c in children] == ['child1', 'child2', 'child3']
    assert window.dom.get_elements('.does-not-exist') == []
    assert window.dom.get_element('#does-not-exist') is None

    # repeated lookups resolve to the same node
    assert window.dom.get_element('#child1') == children[0]
    assert window.dom.get_element('#child1') != children[1]

    assert window.dom.body.tag == 'body'
    assert window.dom.body.children[0].id == 'container'


def special_char_properties_test(window):
    value = 'it\'s "quoted" \\ back\nslash'
    child1 = window.dom.get_element('#child1')

    child1.text = value
    assert child1.text == value

    child1.id = 'id\'with"quotes'
    assert child1.id == 'id\'with"quotes'

    input = window.dom.get_element('#input')
    input.value = value.replace('\n', ' ')  # text inputs strip newlines
    assert input.value == value.replace('\n', ' ')

    child2 = window.dom.get_element('#child2')
    child2.classes.append("it's")
    assert "it's" in list(child2.classes)

    element = window.dom.create_element(f'<p>{value}</p>')
    assert element.text == value


def create_element_test(window):
    # default target is the last child of body
    element = window.dom.create_element('<p id="last">last</p>')
    assert window.dom.body.children[-1] == element

    element = window.dom.create_element(
        '<p id="first">first</p>', '#container', webview.dom.ManipulationMode.FirstChild
    )
    assert element.parent.id == 'container'
    assert window.dom.get_element('#container').children[0].id == 'first'

    element = window.dom.get_element('#container2').append(
        '<span>before</span>', webview.dom.ManipulationMode.Before
    )
    assert element.next.id == 'container2'


def copy_with_events_test(window):
    clicked = []

    def click_handler(event):
        clicked.append(event['target']['id'])

    button = window.dom.get_element('#button')
    button.events.click += click_handler

    copy = button.copy(id='button-copy')
    assert copy.id == 'button-copy'
    assert button.id == 'button'
    assert copy.parent.id == 'container2'

    window.evaluate_js('document.getElementById("button-copy").click()')
    assert wait_for(lambda: clicked)
    assert clicked == ['button-copy']


def removed_element_test(window):
    button = window.dom.get_element('#button')
    button.events.click += lambda e: None
    assert window.evaluate_js('Object.keys(pywebview._eventHandlers).length') == 1

    button.remove()
    assert window.dom.get_element('#button') is None
    assert window.evaluate_js('Object.keys(pywebview._eventHandlers).length') == 0

    # accessing a removed element warns and returns None instead of raising
    assert button.text is None
    assert button.parent is None

    # same for an element removed outside of the Python API
    child1 = window.dom.get_element('#child1')
    window.evaluate_js('document.getElementById("child1").remove()')
    assert child1.text is None


def event_handler_options_test(window):
    from webview.dom import DOMEventHandler

    window.dom.get_element('#container2').append('<input type="checkbox" id="checkbox"/>')
    calls = {'checkbox': 0, 'button': 0, 'container': 0, 'debounced': 0}

    def counter(key):
        def handler(event):
            calls[key] += 1

        return handler

    # prevent_default keeps the checkbox unchecked
    checkbox = window.dom.get_element('#checkbox')
    checkbox.events.click += DOMEventHandler(counter('checkbox'), prevent_default=True)
    window.evaluate_js('document.getElementById("checkbox").click()')
    assert wait_for(lambda: calls['checkbox'] == 1)
    assert not window.evaluate_js('document.getElementById("checkbox").checked')

    # stop_propagation keeps the event from bubbling to the parent
    container2 = window.dom.get_element('#container2')
    container2.events.click += counter('container')
    button = window.dom.get_element('#button')
    button.events.click += DOMEventHandler(counter('button'), stop_propagation=True)
    window.evaluate_js('document.getElementById("button").click()')
    assert wait_for(lambda: calls['button'] == 1)
    sleep(0.3)
    assert calls['container'] == 0

    # debounce collapses a burst of events into a single call
    child1 = window.dom.get_element('#child1')
    child1.events.click += DOMEventHandler(counter('debounced'), debounce=100)
    window.evaluate_js(
        'var el = document.getElementById("child1"); el.click(); el.click(); el.click()'
    )
    assert wait_for(lambda: calls['debounced'] >= 1)
    sleep(0.3)
    assert calls['debounced'] == 1


def views_test(window):
    child1 = window.dom.get_element('#child1')
    assert repr(child1) == str(child1) == child1.node['outerHTML']
    assert repr(window.dom.document) == 'document'
    assert repr(window.dom.window) == 'window'
    window_node = window.dom.window.node
    assert window_node['_pywebviewId'] == 'window'
    assert window_node['scrollY'] == 0

    # an element with listeners is the one the DOM returns
    document = window.dom.document
    document.on('click', lambda e: None)
    assert window.dom.document is document

    window.run_js("document.getElementById('child1').className = ' a  b\\tc '")
    assert len(child1.classes) == 3
    assert str(child1.classes) == repr(child1.classes) == "['a', 'b', 'c']"

    # pywebview identifies the element by data-pywebview-id, so it cannot be overwritten
    node_id = child1._node_id
    child1.attributes['data-pywebview-id'] = 'other'
    child1.attributes.update({'data-pywebview-id': 'other', 'data-ok': 'yes'})
    assert window.dom.get_element('#child1')._node_id == node_id
    assert child1.text == 'DUDE'

    attributes = child1.attributes.copy()
    assert attributes['data-ok'] == 'yes'
    assert 'data-pywebview-id' not in attributes
    assert str(child1.attributes) == repr(child1.attributes) == str(attributes)
    assert child1.attributes.pop('data-ok') == 'yes'
    assert child1.attributes.get('missing', 'default') == 'default'

    child1.attributes.clear()
    assert child1.attributes.copy() == {}
    assert window.dom.get_element('#child1') is None  # its id was cleared too
    assert child1.text == 'DUDE'
