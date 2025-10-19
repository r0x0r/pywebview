import sys

import pytest

import webview

from .util import run_test


def load_css(window):
    window.load_css('body { background: transparent !important; }')


@pytest.mark.skipif(sys.platform != 'darwin', reason='vibrancy is macOS only')
def test_vibrancy():
    window = webview.create_window(
        'set vibrancy example',
        'https://pywebview.flowrl.com/hello',
        transparent=True,
        vibrancy=True,
    )
    run_test(webview, window, start_args={'func': load_css, 'args': window})
