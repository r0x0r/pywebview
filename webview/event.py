import threading


class Event:
    def __init__(self):
        self._items = []
        self._event = threading.Event()

    def set(self, *args, **kwargs):
        for func in self._items:
            func(*args, **kwargs)

        self._event.set()

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
