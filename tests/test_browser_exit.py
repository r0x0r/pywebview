import ctypes
import logging
import os
import signal
import threading
import time

import pytest

import webview

from .util import run_test


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') != 'win32',
    reason='tests how the win32 backend outlives the WebView2 browser process',
)
@pytest.mark.parametrize('transparent', [False, True])
def test_browser_exit(transparent):
    window = webview.create_window(
        'Browser exit', html='<p>Browser exit</p>', transparent=transparent
    )
    run_test(webview, window, browser_exit)


class _Records(logging.Handler):
    def __init__(self):
        super().__init__(logging.ERROR)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def browser_exit(window):
    from webview.platforms.win32_webview2 import _enqueue

    window.events.loaded.wait()
    browser = window.native.browser
    process_ids = []
    got_process_id = threading.Event()

    def get_process_id():
        process_ids.append(int(browser.webview.browser_process_id))
        got_process_id.set()

    # WebView2 is called on its own thread.
    _enqueue(get_process_id)
    assert got_process_id.wait(5)

    records = _Records()
    logger = logging.getLogger('pywebview')
    logger.addHandler(records)
    try:
        os.kill(process_ids[0], signal.SIGTERM)
        deadline = time.monotonic() + 10
        while browser.controller is not None and time.monotonic() < deadline:
            time.sleep(0.1)
        assert browser.controller is None

        # The window still works, without its page.
        post_message = ctypes.WinDLL('user32').PostMessageW
        post_message.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        position = (50 << 16) | 50
        post_message(window.native.hwnd, 0x0201, 0x0001, position)  # WM_LBUTTONDOWN, MK_LBUTTON
        post_message(window.native.hwnd, 0x0202, 0, position)  # WM_LBUTTONUP
        window.resize(500, 400)
        window.move(100, 100)
        window.hide()
        window.show()
        time.sleep(0.5)
    finally:
        logger.removeHandler(records)

    assert records.messages == ['The WebView2 browser process exited: UNEXPECTED']
