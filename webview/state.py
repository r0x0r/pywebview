import json
import sys
from collections.abc import Callable
from threading import Thread
from typing import Any

from typing_extensions import Self

from webview.util import call_maybe_async, escape_string

if sys.version_info >= (3, 11):
    from enum import StrEnum  # Python 3.11 and above
else:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class StateEventType(StrEnum):
    CHANGE = 'change'
    DELETE = 'delete'


_MISSING = object()
# Prefix of a key that state.js stores without sending the change back to Python
_HALT_UPDATE = '__pywebviewHaltUpdate__'


class State(dict):
    _serializable = False

    def __init__(self, window: Any) -> None:
        self.__event_handlers: list[Callable[..., Any]] = []
        self.__window = window

    def __notify_handlers(self, type: StateEventType, key: str, value: Any = None) -> None:
        def notify_handlers():
            for handler in self.__event_handlers:
                if callable(handler):
                    call_maybe_async(handler, type, key, value)

        Thread(target=notify_handlers).start()

    def _set_state_value(self, key: str, value: Any, should_update_js: bool = True) -> None:
        """Internal method to set state values, used by both __setattr__ and __setitem__"""
        if key in self and super().get(key) == value:
            return

        super().__setitem__(key, value)

        if not should_update_js:
            self.__notify_handlers(StateEventType.CHANGE, key, value)
            return

        def update_and_notify():
            self.__window._run_js_api_js(
                f'window.pywebview.state[{json.dumps(_HALT_UPDATE + key)}] = '
                f"JSON.parse('{escape_string(json.dumps(value))}')"
            )
            self.__notify_handlers(StateEventType.CHANGE, key, value)

        if self.__window.events.loaded.is_set():
            update_and_notify()
        else:
            self.__window.events.loaded += update_and_notify

    def _delete_state_value(self, key: str, should_update_js: bool = True) -> Any:
        """Internal method to delete state values, used by both __delattr__ and __delitem__"""
        if key not in self:
            return _MISSING

        old_value = super().pop(key)
        if should_update_js:
            self.__window._run_js_api_js(
                f'delete window.pywebview.state[{json.dumps(_HALT_UPDATE + key)}]'
            )

        self.__notify_handlers(StateEventType.DELETE, key, old_value)
        return old_value

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith('_State__'):
            super().__setattr__(key, value)
        else:
            self._set_state_value(key, value)

    def __getattr__(self, key: str) -> Any:
        if key in self:
            return self[key]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __delattr__(self, key: str) -> None:
        if self._delete_state_value(key) is _MISSING:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __setitem__(self, key: str, value: Any) -> None:
        """Support dictionary-style assignment: state['key'] = value"""
        self._set_state_value(key, value)

    def __delitem__(self, key: str) -> None:
        """Support dictionary-style deletion: del state['key']"""
        if self._delete_state_value(key) is _MISSING:
            raise KeyError(key)

    def __add__(self, item: Callable[..., Any]) -> Self:
        self.__event_handlers.append(item)
        return self

    def __sub__(self, item: Callable[..., Any]) -> Self:
        self.__event_handlers.remove(item)
        return self

    __iadd__ = __add__
    __isub__ = __sub__
