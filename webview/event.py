import multiprocessing
import threading
import logging


logger = logging.getLogger('pywebview')


class Event:
    def __init__(self):
        self._items = []
        self._event = threading.Event()

    def _initialize(self, is_multiprocessing):
        if is_multiprocessing:
            self._event = multiprocessing.Event()

    def set(self, *args, **kwargs):
        for func in self._items:
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.exception(e)

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
