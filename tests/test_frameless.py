import os

import pytest

import webview

from .util import run_test


@pytest.mark.skipif(os.environ.get('PYWEBVIEW_GUI') == 'qt', reason='This test  crashes PyQt5')
def test_frameless():
    window = webview.create_window('Frameless test', 'https://www.example.org', frameless=True)
    run_test(webview, window)
