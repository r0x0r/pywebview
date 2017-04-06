import threading
import time
import pytest
import sys
from multiprocessing import Process


def destroy_window(webview, delay=3):
    def stop():
        time.sleep(delay)
        webview.destroy_window()

    t = threading.Thread(target=stop)
    t.start()


def run_test(test_func):
    try:
        p = Process(target=test_func)
        p.start()
        p.join()
        assert p.exitcode == 0
    except Exception as e:
        pytest.fail('Exception occured: \n{0}'.format(e))
