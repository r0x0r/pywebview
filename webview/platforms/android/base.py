from threading import Semaphore

from android.activity import register_activity_lifecycle_callbacks  # noqa
from android.runnable import run_on_ui_thread  # noqa

from webview.platforms.android.event import EventDispatcher
from webview.platforms.android.jclass.view import Choreographer
from webview.platforms.android.jinterface.view import FrameCallback

# Both proxies below are created once per process and never released. pyjnius
# hands Java a bare pointer to the Python object and keeps the proxy alive
# through a JNI global reference owned by that object, so collecting it leaves
# Android holding a dangling reference - and using one aborts the process with
# "JNI DETECTED ERROR IN APPLICATION: use of deleted global reference".
#
# Creating them per event loop, as this module used to, meant freeing one on
# every window teardown. Their lifetime belongs to the process, not to a window.
_lifecycle_callbacks = None
_choreographer = None
_frame_callback = None

# The event loop whose app lifecycle events are dispatched to, and the semaphore
# the next frame releases. Both belong to the single event loop that is running:
# Android supports one window, and a new one only ever replaces a closed one.
_current_loop = None
_frame_lock = None

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


def _do_frame(_):
    lock = _frame_lock

    if lock is not None:
        lock.release()


# Decorated once, at module level. run_on_ui_thread caches a Runnable per
# function object in a dict that is never pruned, so decorating a function
# rebuilt per event loop would add a permanent entry - and a JNI global
# reference - for every window.
@run_on_ui_thread
def _post_frame():
    global _choreographer, _frame_callback

    if _choreographer is None:
        _choreographer = Choreographer.getInstance()
    if _frame_callback is None:
        _frame_callback = FrameCallback(_do_frame)

    _choreographer.postFrameCallback(_frame_callback)


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

        _current_loop = self
        _register_lifecycle_callbacks()

    def mainloop(self):
        global _frame_lock

        while not self.quit and self.status == 'created':
            lock = Semaphore(0)
            _frame_lock = lock
            _post_frame()
            lock.acquire()

    def close(self):
        global _current_loop

        self.quit = True
        self.status = 'destroyed'

        if _current_loop is self:
            _current_loop = None
