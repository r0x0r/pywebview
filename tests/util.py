import threading
import time
import sys
import logging
import traceback
import pytest
from multiprocessing import Process, Queue

logger = logging.getLogger(__name__)

def run_test(main_func, thread_func=None, param=None, no_destroy=False):
    __tracebackhide__ = True
    queue = Queue()
    p = Process(target=_create_window, args=(main_func, thread_func, queue, param, no_destroy))
    p.start()
    p.join()
    assert p.exitcode == 0

    if not queue.empty():
        exception = queue.get()
        pytest.fail(exception)


def assert_js(webview, func_name, expected_result, uid='master'):
    execute_func = 'window.pywebview.api.{0}()'.format(func_name)
    check_func = 'window.pywebview._returnValues["{0}"].value'.format(func_name)

    webview.evaluate_js(execute_func, uid)

    result = webview.evaluate_js(check_func, uid)
    counter, MAX = 0, 50

    while result is None:
        if counter == MAX:
            raise AssertionError('assert_js timeout')
        else:
            counter += 1
            time.sleep(0.1)
            result = webview.evaluate_js(check_func, uid)

    assert expected_result == result


def _create_window(main_func, thread_func, queue, param, no_destroy):
    import webview

    def thread(destroy_event, param):
        try:
            if thread_func:
                thread_func()
            destroy_event.set()
        except Exception as e:
            logger.exception(e, exc_info=True)
            queue.put(traceback.format_exc())
            destroy_event.set()

    if not no_destroy:
        args = (param,) if param else ()
        destroy_event = _destroy_window(webview)

        t = threading.Thread(target=thread, args=(destroy_event, args))
        t.start()

    main_func()


def _destroy_window(webview, delay=0):
    def stop():
        event.wait()
        time.sleep(delay)
        webview.destroy_window()

        #if sys.platform == 'darwin':
        #    from .util_cocoa import mouseMoveRelative

         #   mouseMoveRelative(1, 1)

    event = threading.Event()
    event.clear()
    t = threading.Thread(target=stop)
    t.start()

    return event


