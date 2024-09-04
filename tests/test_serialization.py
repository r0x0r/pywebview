
import webview
import json
from .util import run_test
import pytest

test_values = [
    ('int', 1),
    ('string', 'test'),
    ('null_value', None),
    ('object', {'key1': 'value', 'key2': 420}),
    ('array', [1, 2, 3]),
    ('mixed', {'key1': 'value', 'key2': [ 1, 2, {'id': 2}], 'nullValue': None}),
    ('boolean', True),
]

test_value_string = '\n'.join([ f"var {name} = {json.dumps(value)}" for name, value in test_values])

HTML = f"""
<!DOCTYPE html>
<html>
<head>

</head>
<body style="width: 100%; height: 100vh; display: flex;">

<script>
{test_value_string}
var circular = {{key: "test"}}
circular.circular = circular
var testObject = {{id: 1}}
var nonCircular = [testObject, testObject]

var nodes = document.getElementsByTagName("div")
</script>
<div>1</div>
<div style="font-family: Helvetica, Arial, sans-serif; font-size: 34px; font-style: italic; font-weight: 800; width: 100%; display: flex; justify-content; center; align-items: center;">
<h1>THIS IS ONLY A TEST</h1>
</h1></div>
<div>3</div>
</body>
</html>
"""

def test_basic_serialization():
    window = webview.create_window('Basic serialization test', html=HTML)
    run_test(webview, window, serialization)


def test_circular_serialization():
    window = webview.create_window('Circular reference test', html=HTML)
    run_test(webview, window, circular_reference)


def test_dom_serialization():
    window = webview.create_window('DOM serialization test', html=HTML)
    run_test(webview, window, dom_serialization)


def serialization(window):
    for name, expected_value in test_values:
        result = window.evaluate_js(name)
        assert result == expected_value

def circular_reference(window):
    result = window.evaluate_js('circular')
    assert result == {'key': 'test', 'circular': '[Circular Reference]'}

    result = window.evaluate_js('nonCircular')
    assert result == [{'id': 1}, {'id': 1}]


def dom_serialization(window):
    result = window.evaluate_js('nodes')
    assert len(result) == 3
    assert result[0]['innerText'] == '1'
    assert result[1]['innerText'].strip() == 'THIS IS ONLY A TEST'
    assert result[2]['innerText'] == '3'
