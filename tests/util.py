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


def assert_js(webview, func_name, expected_result, uid='master'):
    execute_func = 'window.pywebview.api.{0}()'.format(func_name)
    check_func =  """
        var result = window.pywebview._returnValues['{0}']
        result.value
    """.format(func_name)

    webview.evaluate_js(execute_func, uid)

    result = webview.evaluate_js(check_func, uid)

    while result is None:
        time.sleep(0.1)
        result = webview.evaluate_js(check_func, uid)

    assert expected_result == result