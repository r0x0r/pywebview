import webview
from .util import run_test


def test_token():
    window = webview.create_window('Token test')
    run_test(webview, window, token_test)

def test_persistance():
    window = webview.create_window('Token persistance test')
    run_test(webview, window, persistance_test)


def token_test(window):
    token = window.evaluate_js('window.pywebview.token')
    assert token is not None
    assert len(token) > 0


def persistance_test(window):
    token1 = window.evaluate_js('pywebview.token')
    assert token1 is not None

    window.load_html('<div>new HTML</div>')
    token2 = window.evaluate_js('pywebview.token')
    assert token1 == token2

    window.load_url('https://example.org')
    token3 = window.evaluate_js('pywebview.token')
    assert token1 == token2 == token3


