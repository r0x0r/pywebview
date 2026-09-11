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

# Depth of nested should_lock dispatches (closing, before_show, before_load,
# initialized, and on some backends request_sent) currently running *on this
# thread*, across every window. threading.local() rather than a module-level
# int because these events can be dispatched concurrently on different
# threads -- e.g. Cocoa's `request_sent` fires on its own worker thread while a
# lifecycle event fires on the AppKit thread -- so each thread must track its
# own depth without disturbing another thread's.
#
# This is intentionally *not* scoped to a particular `Window`: all of a
# process's windows are normally driven by the one native GUI thread, so if a
# handler for window A's event calls into window B's API, that call is still
# being made by the (only) GUI thread and must not wait on window B's
# readiness event either -- waiting there would block the GUI thread just the
# same, only against a different window's event.
_dispatch_depth = threading.local()

# Identity of the thread that dispatches the lifecycle events marked
# `marks_gui_thread=True` below (closing, before_show, before_load,
# initialized). These are the only events guaranteed, on every backend, to run
# their handlers synchronously on the real native GUI thread -- see the
# architecture rules for `Window`. `request_sent` is also a should_lock event,
# but it is *not* one of these: Cocoa and the WebView2-based backends dispatch
# it on a dedicated worker thread (`_request_executor`), not the GUI thread,
# while GTK dispatches it inline on what happens to be the same thread as its
# lifecycle events. Recording the actual thread identity, rather than assuming
# every should_lock dispatch is "the GUI thread", lets `is_reentrant_dispatch`
# tell these apart per backend without needing to know which backend is
# active. It is set once `Window.__init__` has picked a backend and that
# backend has fired its first lifecycle event; a plain module-level variable
# is safe here because every write stores the same value (there is only one
# such thread per process).
_gui_thread_id: int | None = None


def is_reentrant_dispatch() -> bool:
    """Return whether this thread is currently inside `Event.set()` for a
    should_lock event AND that thread is the real native GUI thread -- i.e.
    whether waiting on a readiness event here would deadlock rather than
    simply delay. Used by `webview.window._api_call()` to recognize such a
    call -- made from a lifecycle handler of *any* window on this process, or
    from a `request_sent` handler on a backend that dispatches it inline on
    the GUI thread -- as reentrant, rather than waiting on it. A
    `request_sent` handler running on a worker thread (Cocoa, WebView2-based
    backends) is not the GUI thread, so it is safe -- and correct -- to let it
    wait normally instead.
    """
    if not getattr(_dispatch_depth, 'depth', 0) > 0:
        return False
    return _gui_thread_id is None or _gui_thread_id == threading.get_ident()


class EventContainer:
    _serializable = False

    if TYPE_CHECKING:

        @type_check_only
        def __getattr__(self, __name: str) -> Event: ...

        @type_check_only
        def __setattr__(self, __name: str, __value: Event) -> None: ...


class Event:
    def __init__(
        self, window: Any, should_lock: bool = False, marks_gui_thread: bool = False
    ) -> None:
        self._items: list[Callable[..., Any]] = []
        self._should_lock = should_lock
        # See `_gui_thread_id` above: True only for the lifecycle events that
        # are guaranteed, on every backend, to dispatch on the real native GUI
        # thread (closing, before_show, before_load, initialized).
        self._marks_gui_thread = marks_gui_thread
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

        if self._marks_gui_thread:
            # Record which thread is dispatching this lifecycle event, so
            # `is_reentrant_dispatch` can later tell a should_lock dispatch
            # made on the real GUI thread apart from one made on a worker
            # thread (e.g. Cocoa/WebView2's `request_sent`). Every write
            # stores the same value, so there is no need to guard this
            # against concurrent writers.
            global _gui_thread_id
            _gui_thread_id = threading.get_ident()

        if len(self._items):
            if self._should_lock:
                # Record, in this thread's local depth counter, that it is for
                # the duration of `execute()` driving a should_lock event
                # synchronously -- see `_dispatch_depth` above for why this is
                # thread-local and shared across windows rather than a value
                # kept on `self._window`. A depth counter rather than a flag
                # keeps this correct if a should_lock event handler itself
                # triggers another should_lock event (on any window) from the
                # same thread.
                previous_depth = getattr(_dispatch_depth, 'depth', 0)
                _dispatch_depth.depth = previous_depth + 1
                try:
                    execute()
                finally:
                    _dispatch_depth.depth = previous_depth
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
