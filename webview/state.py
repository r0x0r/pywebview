import json
from typing import Any, Callable
from typing_extensions import Self
from threading import Thread

try:
    from enum import StrEnum # Python 3.11 and above
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class StateEventType(StrEnum):
    CHANGE = 'change'
    DELETE = 'delete'


class State(dict):

    _serializable = False

    def __init__(self, window):
        self.__event_handlers = []
        self.__window = window

    def __update_js(self, key, value):
        special_key = '__pywebviewHaltUpdate__' + key
        script = f"window.pywebview.state.{special_key} = JSON.parse('{json.dumps(value)}')"
        self.__window.run_js(script)

    def __notify_handlers(self, type, key, value=None):
        def notify_handlers():
            for handler in self.__event_handlers:
                if callable(handler):
                    if type == StateEventType.CHANGE:
                        handler(type, key, value)
                    elif type == StateEventType.DELETE:
                        handler(type, key, value)

        t = Thread(target=notify_handlers)
        t.start()

    def __setattr__(self, key, value, should_update_js=True):
        def update_and_notify():
            self.__update_js(key, value)
            self.__notify_handlers(StateEventType.CHANGE, key, value)

        if key.startswith('_State__'):
            super().__setattr__(key, value)
            return

        if key not in self or self[key] != value:
            self[key] = value

            if not should_update_js:
                self.__notify_handlers(key, value)
                return

            if self.__window.events.loaded.is_set():
                update_and_notify()
            else:
                self.__window.events.loaded += update_and_notify

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'{type(self).__key__}' object has no attribute '{key}'")

    def __delattr__(self, key):
        if key.startswith('__pywebviewHaltUpdate__'):
            key = key.replace('__pywebviewHaltUpdate__', '')
            halt_update = True
        else:
            halt_update = False

        if key in self:
            old_value = self[key]
            del self[key]

            if not halt_update:
                special_key = '__pywebviewHaltUpdate__' + key
                self.__window.run_js(f"delete window.pywebview.state.{special_key}")

            self.__notify_handlers(StateEventType.DELETE, key, old_value)

        else:
            raise AttributeError(f"'{type(self).__key__}' object has no attribute '{key}'")

    def __add__(self, item: Callable[..., Any]) -> Self:
        self.__event_handlers.append(item)
        return self

    def __sub__(self, item: Callable[..., Any]) -> Self:
        self.__event_handlers.remove(item)
        return self

    def __iadd__(self, item: Callable[..., Any]) -> Self:
        self.__event_handlers.append(item)
        return self

    def __isub__(self, item: Callable[..., Any]) -> Self:
        self.__event_handlers.remove(item)
        return self