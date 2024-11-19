import webview
import pytest
from .util import run_test


@pytest.mark.skip
def test_frameless():
    window = webview.create_window('Frameless test', 'https://www.example.org', frameless=True)
    run_test(webview, window)
