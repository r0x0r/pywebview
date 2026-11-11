from __future__ import annotations

import inspect
import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from webview.util import run_async

if TYPE_CHECKING:
    from typing import type_check_only


logger = logging.getLogger('pywebview')

# Number of blocking (should_lock) handlers currently running on each thread.
_blocking_dispatch = threading.local()


def in_blocking_handler() -> bool:
    """Return whether the current thread is running a blocking event handler."""
    return getattr(_blocking_dispatch, 'depth', 0) > 0


class EventContainer:
    _serializable = False

    if TYPE_CHECKING:

        @type_check_only
        def __getattr__(self, __name: str) -> Event: ...

        @type_check_only
        def __setattr__(self, __name: str, __value: Event) -> None: ...


class Event:
    def __init__(self, window: Any, should_lock: bool = False, name: str = '') -> None:
        self._items: list[Callable[..., Any]] = []
        self._should_lock = should_lock
        self._name = name
        self._event = threading.Event()
        self._window = window

    def _async_error(self) -> str:
        return (
            f'window.events.{self._name} is a blocking event and cannot have async handlers. '
            'Use a regular function. To run async code before the window closes, cancel closing '
            'and call window.destroy() when done. '
            'See https://pywebview.flowrl.com/api/#window-events'
        )

    def _check_handler(self, item: Callable[..., Any]) -> None:
        if self._should_lock and inspect.iscoroutinefunction(item):
            raise TypeError(self._async_error())

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

                    if inspect.isawaitable(value):
                        if self._should_lock:
                            # A regular function returned a coroutine (e.g. a lambda wrapping
                            # one). Blocking events cannot wait for it, so discard it.
                            if inspect.iscoroutine(value):
                                value.close()
                            logger.error(self._async_error())
                            continue

                        value = run_async(value)

                    return_values.append(value)

                except Exception as e:
                    logger.exception(e)

        return_values: list[Any] = []

        if len(self._items):
            if self._should_lock:
                _blocking_dispatch.depth = getattr(_blocking_dispatch, 'depth', 0) + 1
                try:
                    execute()
                finally:
                    _blocking_dispatch.depth -= 1
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
        self._check_handler(item)
        self._items.append(item)
        return self

    def __sub__(self, item: Callable[..., Any]) -> Self:
        if item in self._items:
            self._items.remove(item)
        else:
            logger.warning(f'Event handler {item} not found')
        return self

    def __iadd__(self, item: Callable[..., Any]) -> Self:
        self._check_handler(item)
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
