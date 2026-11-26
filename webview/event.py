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
        container = 'window.events' if self._window is not None else 'webview.events'
        return (
            f'{container}.{self._name} is a blocking event and cannot have async handlers. '
            'Use a regular function. To run async code before the window closes, cancel closing '
            'and call window.destroy() when done. '
            'See https://pywebview.flowrl.com/api/#window-events'
        )

    def _check_handler(self, item: Callable[..., Any]) -> None:
        if self._should_lock and (
            inspect.iscoroutinefunction(item)
            or inspect.iscoroutinefunction(getattr(item, '__call__', None))
        ):
            raise TypeError(self._async_error())

    def _execute(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> list[Any]:
        """Run the handlers in the calling thread and return their return values."""
        return_values: list[Any] = []

        for func in self._items:
            try:
                parameters = inspect.signature(func).parameters
                if not parameters:
                    value = func()
                elif self._window is not None and 'window' in parameters:
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

        return return_values

    def _set_in_thread(self, *args: Any, **kwargs: Any) -> None:
        """
        Fire a non-blocking event with its handlers run in the calling thread, so that a caller
        that fires it repeatedly from one thread runs the handlers in firing order.
        """
        self._execute(args, kwargs)
        self._event.set()

    def set(self, *args: Any, **kwargs: Any) -> bool:
        return_values: list[Any] = []

        if self._items:
            if self._should_lock:
                _blocking_dispatch.depth = getattr(_blocking_dispatch, 'depth', 0) + 1
                try:
                    return_values = self._execute(args, kwargs)
                finally:
                    _blocking_dispatch.depth -= 1
            else:
                threading.Thread(target=self._execute, args=(args, kwargs)).start()

        self._event.set()

        return any(value is False for value in return_values)

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

    __iadd__ = __add__
    __isub__ = __sub__

    def __len__(self) -> int:
        return len(self._items)
