from enum import Enum
import json
from typing import Any, Callable
from typing_extensions import Self
from threading import Thread

try:
    from enum import StrEnum # Python 3.11 and above
except ImportError:
    StrEnum = str, Enum

class StateEventType(StrEnum):
    CHANGE = 'change'
    DELETE = 'delete'



class State(dict):
    def __init__(self, window):
        self.__event_handlers = []
        self.__window = window
        super().__init__()

    def __setattr__(self, name, value, should_js_set=True):
        if name.startswith('_State__'):
            super().__setattr__(name, value)
            return

        if name not in self or self[name] != value:
            self[name] = self._wrap_value(value, name)

            if not should_js_set:
                return

            self._js_set(name, value)

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __delattr__(self, name):
        if '__pywebviewHaltUpdate__' in name:
            name = name.replace('__pywebviewHaltUpdate__', '')
            halt_update = True
        else:
            halt_update = False

        if name in self:
            del self[name]

            if not halt_update:

                special_name = self.__generate_halt_name(name)
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

    def _wrap_value(self, value, path):
        if isinstance(value, dict):
            return ObservableDict(value, self, path)
        elif isinstance(value, list):
            return ObservableList(value, self, path)
        return value

    def _js_set(self, name, value):
        if not self.__window.events.loaded.is_set():
            self.__window.events.loaded += lambda: self._js_set(name, value)
            return

        special_name = self.__generate_halt_name(name)
        script = f"window.pywebview.state.{special_name} = JSON.parse('{json.dumps(value)}')"
        self.__window.run_js(script)
        t = Thread(target=self._notify_handlers, args=(StateEventType.CHANGE, name, value))
        t.start()

    def _js_delete(self, name):
        if not self.__window.events.loaded.is_set():
            self.__window.events.loaded += lambda: self._js_delete(name)
            return

        self.__window.run_js(f"delete window.pywebview.state.{name}")
        self._notify_handlers(StateEventType.DELETE, name)

    def _notify_handlers(self, event_type, path, value=None):
        for handler in self.__event_handlers:
            if callable(handler):
                handler(event_type, path, value)

    def __generate_halt_name(self, name):
        return '__pywebviewHaltUpdate__' + name

class ObservableDict(dict):
    def __init__(self, original_dict, state, parent_path):
        super().__init__()
        self.__state = state
        self.__parent_path = parent_path

        # Recursively wrap nested dictionaries and lists
        for key, value in original_dict.items():
            self[key] = self.__state._wrap_value(value, self._get_full_path(key))

    def _get_full_path(self, key):
        return f"{self.__parent_path}.{key}" if self.__parent_path else key

    def __setitem__(self, key, value):
        full_path = self._get_full_path(key)
        super().__setitem__(key, self.__state._wrap_value(value, full_path))
        self.__state._js_set(full_path, value)

    def __delitem__(self, key):
        super().__delitem__(key)
        full_path = self._get_full_path(key)
        self.__state._js_delete(full_path)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        # Ensure nested dictionaries are wrapped when accessed
        if isinstance(value, dict) and not isinstance(value, ObservableDict):
            value = ObservableDict(value, self.__state, self._get_full_path(key))
            super().__setitem__(key, value)
        return value

class ObservableList(list):
    def __init__(self, original_list, state, parent_path):
        super().__init__()
        self.__state = state
        self.__parent_path = parent_path

        # Recursively wrap nested dictionaries and lists
        for index, value in enumerate(original_list):
            self.append(self.__state._wrap_value(value, self._get_full_path(index)))

    def _get_full_path(self, index):
        return f"{self.__parent_path}[{index}]"

    def __setitem__(self, index, value):
        full_path = self._get_full_path(index)
        super().__setitem__(index, self.__state._wrap_value(value, full_path))
        self.__state._js_set(full_path, value)

    def __delitem__(self, index):
        super().__delitem__(index)
        full_path = self._get_full_path(index)
        self.__state._js_delete(full_path)

    def append(self, value):
        full_path = self._get_full_path(len(self))
        super().append(self.__state._wrap_value(value, full_path))
        self.__state._js_set(full_path, value)

    def extend(self, iterable):
        start_index = len(self)
        super().extend(self.__state._wrap_value(item, self._get_full_path(start_index + i)) for i, item in enumerate(iterable))
        for i, value in enumerate(iterable, start=start_index):
            self.__state._js_set(self._get_full_path(i), value)

    def pop(self, index=-1):
        full_path = self._get_full_path(index)
        value = super().pop(index)
        self.__state._js_delete(full_path)

        return value

    def remove(self, value):
        index = self.index(value)
        full_path = self._get_full_path(index)
        super().remove(value)
        self.__state._js_delete(full_path)

    def clear(self):
        for i in range(len(self)):
            self.__state._js_delete(self._get_full_path(i))
        super().clear()