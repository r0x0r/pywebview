import multiprocessing
import threading
import logging
import webview

logger = logging.getLogger('pywebview')


class Event:
    def __init__(self, should_lock=False):
        self._items = []
        self._should_lock = should_lock
        self._event = threading.Event()

    def _initialize(self, is_multiprocessing):
        if is_multiprocessing:
            self._event = multiprocessing.Event()

    def set(self, *args, **kwargs):
        def execute():
            for func in self._items:
                try:
                    func(*args, **kwargs)

                except Exception as e:
                    logger.exception(e)

            if self._should_lock:
                semaphore.release()

        semaphore = threading.Semaphore(0)

        if len(self._items):
            t = threading.Thread(target=execute)
            t.start()

            if self._should_lock:
                semaphore.acquire()

        self._event.set()

    def is_set(self):
        return self._event.is_set()

    def wait(self, timeout=0):
        return self._event.wait(timeout)

    def clear(self):
        return self._event.clear()

    def __add__(self, item):
        self._items.append(item)
        return self

    def __sub__(self, item):
        self._items.remove(item)
        return self

    def __iadd__(self, item):
        self._items.append(item)
        return self

    def __isub__(self, item):
        self._items.remove(item)
        return self
