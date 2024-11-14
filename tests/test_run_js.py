import pytest

import webview

from .util import run_test


@pytest.fixture
def window():
    return webview.create_window('Run JS test', html='<html><body><div id="node">TEST</div></body></html>')



def test_string(window):
    run_test(webview, window, string_test)


def test_int(window):
    run_test(webview, window, int_test)


def string_test(window):
    result = window.run_js(
    """
    "this is only a test"
    """
    )
    assert result == 'this is only a test'


def int_test(window):
    result = window.run_js(
    """
    420
    """
    )
    assert result == 420


def numeric_test(window):
    result = window.run_js(
    """
    '420'
    """
    )
    assert result == '420'
