from threading import Lock

import pytest

import webview

from .util import run_test, wait_release


@pytest.fixture
def window():
    return webview.create_window(
        'Evaluate JS test', html='<html><body><div id="node">TEST</div></body></html>'
    )


def test_state(window):
    run_test(webview, window, state_test)


def test_state_before_start(window):
    window.state.test = 420
    run_test(webview, window, before_start_test)


def test_state_from_js(window):
    run_test(webview, window, state_from_js_test)


def test_state_dict(window):
    run_test(webview, window, state_dict_test)


def test_state_none(window):
    run_test(webview, window, state_none_test)


def test_persistence(window):
    run_test(webview, window, persistence_test)


def test_delete(window):
    run_test(webview, window, delete_test)


def test_delete_from_js(window):
    run_test(webview, window, delete_from_js_test)


def test_event_change(window):
    run_test(webview, window, event_change_test)


def test_event_change_js(window):
    run_test(webview, window, event_change_js_test)


def test_event_delete(window):
    run_test(webview, window, event_delete_test)


def test_event_delete_js(window):
    run_test(webview, window, event_delete_js_test)


def test_event_change_from_js(window):
    run_test(webview, window, event_change_from_js_test)


def test_event_delete_from_js(window):
    run_test(webview, window, event_delete_from_js_test)


def test_string_quotes(window):
    run_test(webview, window, string_quotes_test)


def test_string_quotes_from_js(window):
    run_test(webview, window, string_quotes_from_js_test)


def test_state_dictionary_access(window):
    """Test dictionary-style access: state['key']"""
    run_test(webview, window, dictionary_access_test)


def test_state_dictionary_assignment(window):
    """Test dictionary-style assignment: state['key'] = value"""
    run_test(webview, window, dictionary_assignment_test)


def test_state_dictionary_deletion(window):
    """Test dictionary-style deletion: del state['key']"""
    run_test(webview, window, dictionary_deletion_test)


def test_state_mixed_access(window):
    """Test mixing attribute and dictionary access"""
    run_test(webview, window, mixed_access_test)


def state_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')


def before_start_test(window):
    assert window.evaluate_js('pywebview.state.test === 420')


def state_from_js_test(window):
    window.run_js('pywebview.state.test = 420')
    assert window.state.test == 420


def state_dict_test(window):
    window.state.test = {'test1': 'test1', 'test2': 2}
    assert window.evaluate_js(
        'JSON.stringify(pywebview.state.test) === JSON.stringify({ "test1": "test1", "test2": 2}) '
    )


def state_none_test(window):
    window.state.test = None
    assert window.evaluate_js('pywebview.state.test === null')


def persistence_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')

    window.load_html('<html><body>Reloaded</body></html>')
    assert window.evaluate_js('pywebview.state.test === 420')

    window.load_url('https://www.example.com')
    assert window.evaluate_js('pywebview.state.test === 420')


def delete_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')
    del window.state.test
    assert window.evaluate_js('Object.keys(pywebview.state).length === 0')


def delete_from_js_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')
    window.run_js('delete pywebview.state.test')
    assert 'test' not in window.state


def event_change_test(window):
    def on_change(event, name, value):
        try:
            assert event == 'change'
            assert name == 'test'
            assert value == 420
        except AssertionError as e:
            nonlocal exception
            exception = e

        wait_release(lock)

    lock = Lock()
    exception = False
    window.state += on_change
    window.state.test = 420
    assert lock.acquire(3)
    if exception:
        raise exception


def event_change_js_test(window):
    def on_change(event, name, value):
        try:
            assert event == 'change'
            assert name == 'test'
            assert value == 420
        except AssertionError as e:
            nonlocal exception
            exception = e

        wait_release(lock)

    lock = Lock()
    exception = False
    window.state += on_change
    window.evaluate_js('pywebview.state.test = 420')
    assert lock.acquire(3)
    if exception:
        raise exception


def event_delete_test(window):
    def on_delete(event, name, value):
        try:
            assert event == 'delete'
            assert name == 'test'
            assert value == 420
        except AssertionError as e:
            nonlocal exception
            exception = e

        wait_release(lock)

    exception = False
    lock = Lock()
    window.state.test = 420
    window.state += on_delete
    del window.state.test
    assert lock.acquire(3)

    if exception:
        raise exception


def event_delete_js_test(window):
    def on_delete(event, name, value):
        try:
            assert event == 'delete'
            assert name == 'test'
            assert value == 420
        except AssertionError as e:
            nonlocal exception
            exception = e

        wait_release(lock)

    lock = Lock()
    exception = False
    window.state.test = 420
    window.state += on_delete
    window.evaluate_js('delete pywebview.state.test')
    assert lock.acquire(3)

    if exception:
        raise exception


def event_change_from_js_test(window):
    window.run_js(
        'pywebview.state.addEventListener("change", event => { pywebview.state.result = `${event.detail.key}: ${event.detail.value}` })'
    )
    window.state.test = 0
    assert window.state.result == 'test: 0'


def event_delete_from_js_test(window):
    window.run_js(
        'pywebview.state.addEventListener("delete", event => { pywebview.state.result = event.detail.key })'
    )
    window.state.test = 0
    assert window.evaluate_js('pywebview.state.test == 0')
    del window.state.test
    assert window.state.result == 'test'


def string_quotes_test(window):
    # Test string with single quotes
    window.state.single_quote_string = "String with 'single' quotes inside"
    result = window.evaluate_js('pywebview.state.single_quote_string')
    assert result == "String with 'single' quotes inside"

    # Test string with double quotes
    window.state.double_quote_string = 'String with "double" quotes inside'
    result = window.evaluate_js('pywebview.state.double_quote_string')
    assert result == 'String with "double" quotes inside'

    # Test string with both single and double quotes
    window.state.mixed_quote_string = """String with 'single' and "double" quotes"""
    result = window.evaluate_js('pywebview.state.mixed_quote_string')
    assert result == """String with 'single' and "double" quotes"""

    # Test string with backslashes
    window.state.backslash_string = 'Path\\to\\file\\with\\backslashes'
    result = window.evaluate_js('pywebview.state.backslash_string')
    assert result == 'Path\\to\\file\\with\\backslashes'

    # Test string with line breaks
    window.state.multiline_string = 'Line 1\nLine 2\nLine 3'
    result = window.evaluate_js('pywebview.state.multiline_string')
    assert result == 'Line 1\nLine 2\nLine 3'

    # Test string with tabs and carriage returns
    window.state.special_chars = 'Tab\there\tand\rcarriage\rreturn'
    result = window.evaluate_js('pywebview.state.special_chars')
    assert result == 'Tab\there\tand\rcarriage\rreturn'

    # Test string with escaped characters
    window.state.escaped_string = 'Quote: " Backslash: \\ Newline: \n Tab: \t'
    result = window.evaluate_js('pywebview.state.escaped_string')
    assert result == 'Quote: " Backslash: \\ Newline: \n Tab: \t'

    # Test assignment from JS side with single quotes
    window.run_js('pywebview.state.js_single = "JS string with \'single\' quotes"')
    assert window.state.js_single == "JS string with 'single' quotes"

    # Test assignment from JS side with double quotes
    window.run_js('pywebview.state.js_double = \'JS string with "double" quotes\'')
    assert window.state.js_double == 'JS string with "double" quotes'

    # Test roundtrip: Python -> JS -> Python with mixed quotes and special chars
    test_string = """Test with 'single' and "double" quotes\nand backslash\\path"""
    window.state.roundtrip_test = test_string
    js_result = window.evaluate_js('pywebview.state.roundtrip_test')
    assert js_result == test_string


def string_quotes_from_js_test(window):
    # Test assignment from JS with single quotes inside double quotes
    window.run_js(
        'pywebview.state.js_single_in_double = "JavaScript string with \'single\' quotes"'
    )
    assert window.state.js_single_in_double == "JavaScript string with 'single' quotes"

    # Test assignment from JS with double quotes inside single quotes
    window.run_js(
        'pywebview.state.js_double_in_single = \'JavaScript string with "double" quotes\''
    )
    assert window.state.js_double_in_single == 'JavaScript string with "double" quotes'

    # Test assignment from JS with escaped single quotes
    window.run_js("pywebview.state.js_escaped_single = 'String with \\'escaped\\' quotes'")
    assert window.state.js_escaped_single == "String with 'escaped' quotes"

    # Test assignment from JS with escaped double quotes
    window.run_js('pywebview.state.js_escaped_double = "String with \\"escaped\\" quotes"')
    assert window.state.js_escaped_double == 'String with "escaped" quotes'

    # Test assignment from JS with backslashes
    window.run_js('pywebview.state.js_backslash = "C:\\\\Windows\\\\System32\\\\file.txt"')
    assert window.state.js_backslash == 'C:\\Windows\\System32\\file.txt'

    # Test assignment from JS with line breaks
    window.run_js('pywebview.state.js_multiline = "First line\\nSecond line\\nThird line"')
    assert window.state.js_multiline == 'First line\nSecond line\nThird line'

    # Test assignment from JS with tabs and other escape sequences
    window.run_js('pywebview.state.js_tabs = "Column1\\tColumn2\\tColumn3\\r\\nNew row"')
    assert window.state.js_tabs == 'Column1\tColumn2\tColumn3\r\nNew row'

    # Test assignment from JS with mixed quotes using template literals
    window.run_js(
        'pywebview.state.js_template = `Template with \'single\' and "double" quotes\\nwith newline`'
    )
    assert (
        window.state.js_template == """Template with 'single' and "double" quotes\nwith newline"""
    )

    # Test assignment from JS with Unicode characters
    window.run_js(
        'pywebview.state.js_unicode = "Unicode: \\u0048\\u0065\\u006C\\u006C\\u006F \\u2764\\uFE0F"'
    )
    assert window.state.js_unicode == 'Unicode: Hello ❤️'

    # Test assignment from JS with null bytes and control characters
    window.run_js('pywebview.state.js_control = "Before\\u0000null\\u0001control\\u0008backspace"')
    assert window.state.js_control == 'Before\x00null\x01control\x08backspace'

    # Test that JS-assigned strings are accessible back in JS
    window.run_js('pywebview.state.js_test = "Test\\nfrom\\tJS\\\\path"')
    assert window.evaluate_js('pywebview.state.js_test === "Test\\nfrom\\tJS\\\\path"')

    # Test complex string with all special characters from JS
    window.run_js(
        '''pywebview.state.js_complex = "Line 1 with 'quotes'\\nLine 2 with \\"quotes\\"\\tand\\\\backslash"'''
    )
    expected = 'Line 1 with \'quotes\'\nLine 2 with "quotes"\tand\\backslash'
    assert window.state.js_complex == expected

    # Test template literal with complex content
    window.run_js(
        """pywebview.state.js_template_complex = `Multi-line template
with 'single' and "double" quotes
and backslash: \\\\
and tab: \\t end`"""
    )
    expected = """Multi-line template
with 'single' and "double" quotes
and backslash: \\
and tab: \t end"""
    assert window.state.js_template_complex == expected


def dictionary_access_test(window):
    """Test getting values using dictionary syntax"""
    # Set via attribute, get via dictionary
    window.state.test_key = 'test_value'
    assert window.state['test_key'] == 'test_value'

    # Set via dictionary, get via dictionary
    window.state['another_key'] = 'another_value'
    assert window.state['another_key'] == 'another_value'


def dictionary_assignment_test(window):
    """Test setting values using dictionary syntax"""
    # Dictionary-style assignment
    window.state['name'] = 'John'
    window.state['age'] = 30
    window.state['data'] = {'nested': 'object'}

    # Verify via attribute access
    assert window.state.name == 'John'
    assert window.state.age == 30
    assert window.state.data == {'nested': 'object'}

    # Verify in JavaScript
    assert window.evaluate_js('pywebview.state.name === "John"')
    assert window.evaluate_js('pywebview.state.age === 30')


def dictionary_deletion_test(window):
    """Test deleting values using dictionary syntax"""
    # Set some values
    window.state['temp1'] = 'value1'
    window.state['temp2'] = 'value2'

    # Delete using dictionary syntax
    del window.state['temp1']

    # Verify deletion
    assert 'temp1' not in window.state
    assert 'temp2' in window.state

    # Test KeyError for non-existent key
    with pytest.raises(KeyError):
        del window.state['nonexistent']


def mixed_access_test(window):
    """Test mixing attribute and dictionary access patterns"""
    # Set via attribute, access both ways
    window.state.attr_set = 'attribute_value'
    assert window.state.attr_set == 'attribute_value'
    assert window.state['attr_set'] == 'attribute_value'

    # Set via dictionary, access both ways
    window.state['dict_set'] = 'dictionary_value'
    assert window.state['dict_set'] == 'dictionary_value'
    assert window.state.dict_set == 'dictionary_value'

    # Test dictionary methods
    keys = list(window.state.keys())
    assert 'attr_set' in keys
    assert 'dict_set' in keys
    assert len(window.state) >= 2
