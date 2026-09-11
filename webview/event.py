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
            if self._should_lock:
                # Record, on *this thread's* local storage, that it is for the
                # duration of `execute()` driving `self._window` synchronously,
                # so `Window._api_call()` can recognize a call made from one of
                # these handlers as reentrant rather than waiting on it. Using
                # `_reentrant_dispatch` (thread-local) rather than a value
                # shared on the window is required because should_lock events
                # can be dispatched concurrently on different threads -- e.g.
                # Cocoa's `request_sent` fires on its own worker thread while a
                # lifecycle event fires on the AppKit thread -- so each thread
                # must track its own depth without disturbing another thread's.
                # A depth counter rather than a flag also keeps this correct if
                # a should_lock event handler itself triggers another
                # should_lock event on the same thread.
                local_state = getattr(self._window, '_reentrant_dispatch', None)
                if local_state is not None:
                    previous_depth = getattr(local_state, 'depth', 0)
                    local_state.depth = previous_depth + 1
                    try:
                        execute()
                    finally:
                        local_state.depth = previous_depth
                else:
                    # No window (e.g. a standalone `Event(None, True)`) -- there
                    # is nothing to record reentrancy against, just run inline.
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
