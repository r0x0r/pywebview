from enum import Enum
import json
from typing import Any, Callable
from typing_extensions import Self
from threading import Thread


class StateEventType(str, Enum):
    CHANGE = 'change'
    DELETE = 'delete'


class State(dict):

    def __init__(self, window):
        self.__event_handlers = []
        self.__window = window

    def __setattr__(self, name, value, should_update_js=True):
        def update_js():
            special_name = '__pywebviewHaltUpdate__' + name
            script = f"window.pywebview.state.{special_name} = JSON.parse('{json.dumps(value)}')"
            self.__window.run_js(script)
            t = Thread(target=notify_handlers)
            t.start()

        def notify_handlers():
            for handler in self.__event_handlers:
                if callable(handler):
                    handler(StateEventType.CHANGE, name, value)

        if name.startswith('_State__'):
            super().__setattr__(name, value)
            return

        if name not in self or self[name] != value:
            self[name] = value

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
        if name.startswith('__pywebviewHaltUpdate__'):
            name = name.replace('__pywebviewHaltUpdate__', '')
            halt_update = True
        else:
            halt_update = False

        if name in self:
            del self[name]

            if not halt_update:
                special_name = '__pywebviewHaltUpdate__' + name
                self.__window.run_js(f"delete window.pywebview.state.{special_name}")

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