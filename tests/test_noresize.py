import webview
from .util import run_test


def test_noresize():
    window = webview.create_window('Min size test', 'https://www.example.org',
                                   width=800, height=600, resizable=True, min_size=(400, 200))
    run_test(webview, window)


