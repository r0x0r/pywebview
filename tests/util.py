import threading
import time
import sys
import pytest
from multiprocessing import Process, Queue


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


def _create_window(main_func, thread_func, queue, param):
    import webview
    def thread(destroy_event, param):
        try:
            thread_func()
            destroy_event.set()
        except Exception as e:
            queue.put(e)
            destroy_event.set()

    args = (param,) if param else ()
    destroy_event = destroy_window(webview)
    t = threading.Thread(target=thread, args=(destroy_event, args))
    t.start()

    main_func()


def run_test2(main_func, thread_func, webview, param=None):
    queue = Queue()
    p = Process(target=_create_window, args=(main_func, thread_func, queue, param))
    p.start()
    p.join()
    assert p.exitcode == 0

    if not queue.empty():
        exception = queue.get()
        pytest.fail(exception)


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