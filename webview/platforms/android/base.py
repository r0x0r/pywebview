import logging
from collections import deque
from functools import wraps
from threading import Event, RLock

from android.activity import _activity as activity  # noqa
from android.activity import register_activity_lifecycle_callbacks  # noqa

from webview.platforms.android.event import EventDispatcher
from webview.platforms.android.jinterface.lang import Runnable

logger = logging.getLogger('pywebview')

# Process-wide by necessity. pyjnius hands Java a bare pointer to a proxy's
# Python object and ties the proxy's JNI global reference to that object, so
# collecting one leaves Java holding a dangling reference - and using it aborts
# the process with "use of deleted global reference".
_lifecycle_callbacks = None
_ui_runnable = None

# The event loop lifecycle events are dispatched to. Android supports a single
# window, and a new one only ever replaces a closed one.
_current_loop = None

# Serialises use of the runOnUiThread method descriptor. pyjnius binds an
# instance method by writing the receiver onto the shared, class-level
# JavaMethod object, so two threads calling it at once can leave one invoking a
# receiver the other has already released. Reentrant, since Android runs the
# Runnable inline when runOnUiThread is called from the UI thread itself.
_ui_lock = RLock()

# Work queued for the UI thread. One entry is consumed per posted Runnable, so
# a single proxy serves every call site.
_ui_queue: deque = deque()

_LIFECYCLE_EVENTS = {
    'onActivityCreated': 'on_create',
    'onActivityPaused': 'on_pause',
    'onActivityDestroyed': 'on_destroy',
    'onActivityResumed': 'on_resume',
    'onActivityStarted': 'on_start',
    'onActivityStopped': 'on_stop',
}


def _forward(handler):
    def forward(*args):
        loop = _current_loop

        if loop is not None:
            getattr(loop.app, handler)(*args)

    return forward


def _register_lifecycle_callbacks():
    global _lifecycle_callbacks

    if _lifecycle_callbacks is None:
        # Registered for the life of the process. Routing through _current_loop
        # keeps a dismissed view's callbacks from firing without dropping the
        # proxy.
        _lifecycle_callbacks = register_activity_lifecycle_callbacks(
            **{event: _forward(handler) for event, handler in _LIFECYCLE_EVENTS.items()}
        )


def _run_next():
    try:
        func, args, kwargs = _ui_queue.popleft()
    except IndexError:
        return

    try:
        func(*args, **kwargs)
    except Exception:
        logger.exception('Error running %s on the UI thread', getattr(func, '__name__', func))


def run_on_ui_thread(f):
    """Run the decorated function on the Android UI thread.

    Unlike android.runnable.run_on_ui_thread, the call arguments are queued
    rather than stored on a per-function Runnable proxy that is never released
    and that two concurrent calls would overwrite.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        global _ui_runnable

        _ui_queue.append((f, args, kwargs))

        with _ui_lock:
            if _ui_runnable is None:
                _ui_runnable = Runnable(_run_next)

            activity.runOnUiThread(_ui_runnable)

    return wrapper


class EventLoop(EventDispatcher):
    def __init__(self):
        super().__init__()
        from webview.platforms.android.app import App

        global _current_loop

        self.app = App.get_running_app()
        self.quit = False
        self.status = 'idle'
        self.resumed = False
        self.destroyed = False
        self.paused = False
        self._closed = Event()

        _current_loop = self
        _register_lifecycle_callbacks()

    def mainloop(self):
        # Parks the calling thread until the window closes. Nothing here runs
        # per frame, so a Choreographer callback would only add concurrent
        # pyjnius traffic.
        while not self.quit and self.status == 'created':
            self._closed.wait()

    def close(self):
        global _current_loop

        self.quit = True
        self.status = 'destroyed'
        self._closed.set()

        if _current_loop is self:
            _current_loop = None
