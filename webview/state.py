from enum import Enum
import json
from typing import Any, Callable
from typing_extensions import Self


class StateEventType(str, Enum):
    CHANGE = 'change'
    DELETE = 'delete'


class State(dict):

    def __init__(self, window):
        self.__event_handlers = []
        self.__window = window

    def __setattr__(self, name, value, should_update_js=True):
        def update_js():
            script = f"window.pywebview.state.{name} = {{ 'value': JSON.parse('{json.dumps(value)}'), 'pywebviewHaltUpdate': true }}"
            self.__window.run_js(script)

        if name.startswith('_State__'):
            super().__setattr__(name, value)
            return

        if name not in self or self[name] != value:
            self[name] = value

            for handler in self.__event_handlers:
                if callable(handler):
                    handler(StateEventType.CHANGE, name, value)

            if not should_update_js:
                return

            if self.__window.events.loaded.is_set():
                update_js()
            else:
                self.__window.events.loaded += update_js

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __delattr__(self, name):
        try:
            if 'pywebviewHaltUpdate' in name:
                name = json.loads(name)
        except:
            pass

        if isinstance(name, dict) and 'key' in name and name.get('pywebviewHaltUpdate'):
            name = name['key']
            halt_update = True
        else:
            halt_update = False

        if name in self:
            del self[name]

            if not halt_update:
                self.__window.run_js(f"delete window.pywebview.state.{name}")

            for handler in self.__event_handlers:
                if callable(handler):
                    handler(StateEventType.DELETE, name)
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

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