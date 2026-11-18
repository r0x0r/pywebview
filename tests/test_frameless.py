import os
import time

import pytest

import webview

from .util import run_test


@pytest.mark.skipif(os.environ.get('PYWEBVIEW_GUI') == 'qt', reason='This test  crashes PyQt5')
def test_frameless():
    window = webview.create_window('Frameless test', 'https://www.example.org', frameless=True)
    run_test(webview, window)


@pytest.mark.skipif(os.environ.get('PYWEBVIEW_GUI') == 'qt', reason='This test  crashes PyQt5')
def test_frameless_has_no_frame():
    window = webview.create_window(
        'Frameless test', html='<html><body></body></html>', frameless=True, width=400, height=300
    )
    run_test(webview, window, frame_size)


def frame_size(window):
    # The frame is the part of the window height not taken by the page. Compare it with a framed
    # window rather than with zero, as window size and page size may use different units.
    def frame(w):
        time.sleep(0.5)  # let geometry settle
        return w.height - w.evaluate_js('window.innerHeight')

    framed = webview.create_window(
        'Framed window', html='<html><body></body></html>', width=400, height=300
    )
    try:
        assert framed.events.loaded.wait(10)
        framed_frame = frame(framed)
        # Some backends (GTK) report the size without the title bar, so there is nothing to compare
        if framed_frame <= 0:
            pytest.skip('window size does not include the title bar')
        assert frame(window) < framed_frame
    finally:
        framed.destroy()
