import threading
import time
import sys
from multiprocessing import Process


def destroy_window(webview, delay=3):
    def stop():
        time.sleep(delay)
        webview.destroy_window()

        if sys.platform == 'darwin':
            from util_cocoa import mouseMoveRelative

            mouseMoveRelative(1, 1)

    t = threading.Thread(target=stop)
    t.start()


def run_test(test_func, param=None):
    args = (param,) if param else ()
    p = Process(target=test_func, args=args)
    p.start()
    p.join()
    assert p.exitcode == 0
