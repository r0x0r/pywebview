import webview
from .util import run_test


def test_min_size():
    window = webview.create_window('Min size test', 'https://www.example.org', min_size=(400, 200))
    run_test(webview, window)

