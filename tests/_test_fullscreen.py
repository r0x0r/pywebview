import threading
from .util import destroy_window, run_test


def fullscreen():
    import webview

    def _fullscreen(webview):
        assert webview.webview_ready(10)
        destroy_event.set()

    t = threading.Thread(target=_fullscreen, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)
    webview.create_window('Fullscreen test', 'https://www.example.org', fullscreen=True)


def test_fullscreen():
    run_test(fullscreen)
