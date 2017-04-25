import pytest
import sys
import threading
from .util import run_test, destroy_window


def change_url():
    import webview

    def _change_url(webview):
        try:
            webview.change_url('http://www.google.org')
        except Exception as e:
            sys.exit(1)
            pytest.fail('Exception occured: \n{0}'.format(e))

    t = threading.Thread(target=_change_url, args=(webview,))
    t.start()

    destroy_window(webview, 5)
    webview.create_window('URL change test', 'https://www.example.org')
    sys.exit(1)

def test_change_url():
    run_test(change_url)
