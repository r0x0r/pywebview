from __future__ import annotations

import inspect
import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

if TYPE_CHECKING:
    from typing import type_check_only


logger = logging.getLogger('pywebview')


class EventContainer:
    _serializable = False

    if TYPE_CHECKING:

        @type_check_only
        def __getattr__(self, __name: str) -> Event: ...

        @type_check_only
        def __setattr__(self, __name: str, __value: Event) -> None: ...


class Event:
    def __init__(self, window: Any, should_lock: bool = False) -> None:
        self._items: list[Callable[..., Any]] = []
        self._should_lock = should_lock
        self._event = threading.Event()
        self._window = window

    def set(self, *args: Any, **kwargs: Any) -> bool:
        def execute():
            for func in self._items:
                try:
                    if len(inspect.signature(func).parameters.values()) == 0:
                        value = func()
                    elif 'window' in inspect.signature(func).parameters:
                        value = func(self._window, *args, **kwargs)
                    else:
                        value = func(*args, **kwargs)
                    return_values.append(value)

                except Exception as e:
                    logger.exception(e)

        return_values: list[Any] = []

        if len(self._items):
            if self._should_lock and hasattr(self._window, '_gui_thread_ident'):
                # Record that `self._window` is, for the duration of `execute()`,
                # being driven synchronously by this thread (the GUI thread), so
                # `Window._api_call()` can recognize a call made from one of these
                # handlers as reentrant rather than waiting on it. Restore the
                # previous value rather than clearing unconditionally in case a
                # should_lock event is somehow dispatched from within another.
                previous_thread = self._window._gui_thread_ident
                self._window._gui_thread_ident = threading.get_ident()
                try:
                    execute()
                finally:
                    self._window._gui_thread_ident = previous_thread
            else:
                if self._should_lock:
                    execute()
                else:
                    t = threading.Thread(target=execute)
                    t.start()

        false_values = [v for v in return_values if v is False]
        self._event.set()

        return len(false_values) != 0

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)

    def clear(self) -> None:
        return self._event.clear()

    def __add__(self, item: Callable[..., Any]) -> Self:
        self._items.append(item)
        return self

    def __sub__(self, item: Callable[..., Any]) -> Self:
        if item in self._items:
            self._items.remove(item)
        else:
            logger.warning(f'Event handler {item} not found')
        return self

    def __iadd__(self, item: Callable[..., Any]) -> Self:
        self._items.append(item)
        return self

    def __isub__(self, item: Callable[..., Any]) -> Self:
        if item in self._items:
            self._items.remove(item)
        else:
            logger.warning(f'Event handler {item} not found')
        return self

    def __len__(self) -> int:
        return len(self._items)
