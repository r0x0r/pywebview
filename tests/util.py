import threading
import time
import sys
from multiprocessing import Process


def destroy_window(webview, delay=0):
    def stop():
        event.wait()
        time.sleep(delay)
        webview.destroy_window()

        if sys.platform == 'darwin':
            from .util_cocoa import mouseMoveRelative

            mouseMoveRelative(1, 1)

    event = threading.Event()
    event.clear()
    t = threading.Thread(target=stop)
    t.start()

    return event


def run_test(test_func, param=None):
    args = (param,) if param else ()
    p = Process(target=test_func, args=args)
    p.start()
    p.join()
    assert p.exitcode == 0
