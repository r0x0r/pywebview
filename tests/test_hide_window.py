import webview
from .util import run_test


def test_hide_show_window():
    window = webview.create_window('Hide/show window test', 'https://www.example.org', hidden=True)
    run_test(webview, window, hide_show_window)


def hide_show_window(window):
    window.show()
    window.hide()




