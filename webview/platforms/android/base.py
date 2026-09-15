import logging
from collections import deque
from functools import wraps
from threading import Event, RLock

from android.activity import _activity as activity  # noqa
from android.activity import register_activity_lifecycle_callbacks  # noqa

from webview.platforms.android.event import EventDispatcher
from webview.platforms.android.jinterface.lang import Runnable

logger = logging.getLogger('pywebview')

# Everything in this module is deliberately process-wide.
#
# pyjnius hands Java a bare pointer to a proxy's Python object and keeps the
# proxy alive through a JNI global reference owned by that same object, so
# collecting one leaves Java holding a dangling reference - and using it aborts
# the process with "JNI DETECTED ERROR IN APPLICATION: use of deleted global
# reference". Creating these per window, as this module used to, meant freeing
# them on every teardown. Their lifetime belongs to the process.
_lifecycle_callbacks = None
_ui_runnable = None

# The event loop app lifecycle events are dispatched to. Android supports a
# single window, and a new one only ever replaces a closed one.
_current_loop = None

# Serialises use of the runOnUiThread method descriptor. pyjnius binds an
# instance method by writing the receiver onto the *shared*, class-level
# JavaMethod object and then reads it back inside the call, so two threads
# calling the same method at once can leave one of them invoking a receiver the
# other has already released - the second half of the "deleted global
# reference" aborts. Posting is the one Java call this backend makes from more
# than one thread, so it is the one that has to be held apart.
# Reentrant: Android runs the Runnable inline when runOnUiThread is called
# from the UI thread itself, so a posted call can post again underneath us.
_ui_lock = RLock()

# Work queued for the UI thread. One entry is consumed per posted Runnable, so
# a single proxy serves every call site instead of p4a's run_on_ui_thread,
# which builds a Runnable per decorated function and caches it forever.
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
        # is what unregistering used to achieve - stopping a dismissed view's
        # callbacks from firing - without having to drop the proxy.
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

    Replaces android.runnable.run_on_ui_thread, which posts through a Runnable
    proxy built per decorated function and never released, and which stores the
    call's arguments on that shared proxy - so two calls in flight at once
    overwrite each other. Work is queued instead, and posted under _ui_lock.
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
        # Just parks the calling thread until the window closes. This used to
        # post a Choreographer frame callback and wait for it, sixty times a
        # second, which bought nothing: nothing here runs per frame. It did
        # however put sixty Java round trips and sixty Python upcalls a second
        # against whatever the UI thread was doing, which is exactly the
        # concurrent pyjnius traffic the aborts needed.
        while not self.quit and self.status == 'created':
            self._closed.wait()

    def close(self):
        global _current_loop

        self.quit = True
        self.status = 'destroyed'
        self._closed.set()

        if _current_loop is self:
            _current_loop = None
