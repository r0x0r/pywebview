import os

import pytest

import webview

from .util import run_test


@pytest.fixture
def window():
    return webview.create_window('Cookie test', 'assets/test.html')


def test_get_cookies(window):
    run_test(webview, window, get_cookies_test)


@pytest.mark.skipif(os.environ.get('PYWEBVIEW_GUI') == 'qt', reason='This test crashes QT')
def test_clear_cookies(window):
    run_test(webview, window, clear_cookies_test)


def get_cookies_test(window):
    cookies = window.get_cookies()
    assert len(cookies) == 1
    assert cookies[0].output().startswith('Set-Cookie: pywebview=true; Domain=127.0.0.1;')


def clear_cookies_test(window):
    window.clear_cookies()
    cookies = window.get_cookies()
    assert len(cookies) == 0
