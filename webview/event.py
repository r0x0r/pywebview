from __future__ import annotations

import inspect
import logging
import threading
from typing import Any, Callable, TYPE_CHECKING

from typing_extensions import Self

if TYPE_CHECKING:
    from typing import type_check_only



logger = logging.getLogger('pywebview')


class EventContainer:
    def __init__(self):
        self._events: dict[str, Event] = {}
        self._window = None

    def __getattr__(self, name: str) -> Event:
        if name not in self._events:
            # Create a new custom event dynamically
            self._events[name] = Event(self._window, is_custom=True)
        return self._events[name]

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_events'):
                super().__setattr__('_events', {})
            self._events[name] = value

    if TYPE_CHECKING:

        @type_check_only
        def __getattr__(self, __name: str) -> Event:
            ...

        @type_check_only
        def __setattr__(self, __name: str, __value: Event) -> None:
            ...


class Event:
    def __init__(self, window, should_lock: bool = False, is_custom: bool = False) -> None:
        self._items: list[Callable[..., Any]] = []
        self._should_lock = should_lock
        self._event = threading.Event()
        self._window = window
        self.return_values: set[Any] = set()
        self._is_custom = is_custom  # Flag to identify custom events created by user

    def set(self, *args: Any, **kwargs: Any) -> bool:
        def execute():
            self.return_values = set()
            for func in self._items:
                try:
                    # Determine how to call the function based on its signature
                    if len(inspect.signature(func).parameters.values()) == 0:
                        value = func()
                    elif 'window' in inspect.signature(func).parameters:
                        value = func(self._window, *args, **kwargs)
                    else:
                        value = func(*args, **kwargs)
                    self.return_values.add(value)

                except Exception as e:
                    logger.exception(e)

        if len(self._items):
            if self._should_lock:
                execute()
            else:
                t = threading.Thread(target=execute)
                t.start()
                # Only wait for custom events to get return values
                # System events remain non-blocking for performance
                if self._is_custom:
                    t.join()

        # For custom events (created by user): return True by default, False only if any function returns False
        # For default events: keep original behavior
        if self._is_custom:
            false_values = [v for v in self.return_values if v is False]
            result = len(false_values) == 0  # True if no False values found
        else:
            # Original behavior for default events
            false_values = [v for v in self.return_values if v is False]
            result = len(false_values) != 0

        self._event.set()
        return result

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)

    def clear(self) -> None:
        return self._event.clear()

    def __call__(self, *args: Any, **kwargs: Any) -> bool:
        """
        Allows the event to be called as a function to manually fire the event.
        """
        return self.set(*args, **kwargs)

    def __add__(self, item: Callable[..., Any]) -> Self:
        self._items.append(item)
        return self

    def __sub__(self, item: Callable[..., Any]) -> Self:
        self._items.remove(item)
        return self

    def __iadd__(self, item: Callable[..., Any]) -> Self:
        self._items.append(item)
        return self

    def __isub__(self, item: Callable[..., Any]) -> Self:
        self._items.remove(item)
        return self

    def __len__(self) -> int:
        return len(self._items)
