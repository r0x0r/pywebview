import json
from threading import Thread
from typing import Any, Callable

from typing_extensions import Self

from webview.util import escape_string

try:
    from enum import StrEnum  # Python 3.11 and above
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
        script = f"window.pywebview.state.{special_key} = JSON.parse('{escape_string(json.dumps(value))}')"
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

    def _set_state_value(self, key, value, should_update_js=True):
        """Internal method to set state values, used by both __setattr__ and __setitem__"""

        def update_and_notify():
            self.__update_js(key, value)
            self.__notify_handlers(StateEventType.CHANGE, key, value)

        if key not in self or super().get(key) != value:
            super().__setitem__(key, value)

            if not should_update_js:
                self.__notify_handlers(StateEventType.CHANGE, key, value)
                return

            if self.__window.events.loaded.is_set():
                update_and_notify()
            else:
                self.__window.events.loaded += update_and_notify

    def __setattr__(self, key, value, should_update_js=True):
        if key.startswith('_State__'):
            super().__setattr__(key, value)
            return

        self._set_state_value(key, value, should_update_js)

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'{type(self).__key__}' object has no attribute '{key}'")

    def _delete_state_value(self, key, should_update_js=True):
        """Internal method to delete state values, used by both __delattr__ and __delitem__"""
        if key in self:
            old_value = self[key]
            super().__delitem__(key)

            if should_update_js:
                special_key = '__pywebviewHaltUpdate__' + key
                self.__window.run_js(f'delete window.pywebview.state.{special_key}')

            self.__notify_handlers(StateEventType.DELETE, key, old_value)
            return old_value
        return None

    def __delattr__(self, key):
        if key.startswith('__pywebviewHaltUpdate__'):
            key = key.replace('__pywebviewHaltUpdate__', '')
            halt_update = True
        else:
            halt_update = False

        old_value = self._delete_state_value(key, should_update_js=not halt_update)
        if old_value is None:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __getitem__(self, key):
        """Support dictionary-style access: state['key']"""
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        """Support dictionary-style assignment: state['key'] = value"""
        self._set_state_value(key, value, should_update_js=True)

    def __delitem__(self, key):
        """Support dictionary-style deletion: del state['key']"""
        old_value = self._delete_state_value(key, should_update_js=True)
        if old_value is None:
            raise KeyError(key)

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
