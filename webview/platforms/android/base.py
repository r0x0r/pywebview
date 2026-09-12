from threading import Semaphore

from android.activity import (  # noqa
    register_activity_lifecycle_callbacks,
    unregister_activity_lifecycle_callbacks,
)
from android.runnable import run_on_ui_thread  # noqa

from webview.platforms.android.event import EventDispatcher
from webview.platforms.android.jclass.view import Choreographer
from webview.platforms.android.jinterface.view import FrameCallback
from webview.platforms.android.jproxy import retain


class EventLoop(EventDispatcher):
    def __init__(self):
        super().__init__()
        from webview.platforms.android.app import App

        self.app = App.get_running_app()
        self.quit = False
        self.status = 'idle'
        self.resumed = False
        self.destroyed = False
        self.paused = False
        # Kept so close() can detach it; otherwise each new app stacks another
        # live set of callbacks pointing at the previous, dismissed, view.
        self._lifecycle_callbacks = register_activity_lifecycle_callbacks(
            onActivityCreated=self.app.on_create,
            onActivityPaused=self.app.on_pause,
            onActivityDestroyed=self.app.on_destroy,
            onActivityResumed=self.app.on_resume,
            onActivityStarted=self.app.on_start,
            onActivityStopped=self.app.on_stop,
        )

    def mainloop(self):
        choreographer = None
        frame_callback = None
        lock = None

        def do_frame(_):
            lock.release()

        # Defined once, outside the loop. run_on_ui_thread caches a Runnable per
        # function object in a dict that is never pruned, so decorating a
        # function rebuilt every iteration would add a permanent entry - and a
        # JNI global reference - on every frame.
        @run_on_ui_thread
        def post_frame():
            nonlocal choreographer, frame_callback

            if not choreographer:
                choreographer = Choreographer.getInstance()
            if not frame_callback:
                frame_callback = FrameCallback(do_frame)

            choreographer.postFrameCallback(frame_callback)

        while not self.quit and self.status == 'created':
            lock = Semaphore(0)
            post_frame()
            lock.acquire()

    def close(self):
        self.quit = True
        self.status = 'destroyed'

        if self._lifecycle_callbacks is not None:
            # Take ownership *before* unregistering. p4a's module-level set is
            # this proxy's only owner, and unregister_activity_lifecycle_callbacks
            # drops it from that set - which frees the Python object while
            # Android may still be part-way through dispatching to it, leaving a
            # dangling raw pointer behind. Unregistering is still right, so that
            # a dismissed app stops receiving lifecycle events; it just must not
            # take the object with it. See jproxy.retain.
            retain(self._lifecycle_callbacks)
            unregister_activity_lifecycle_callbacks(self._lifecycle_callbacks)
            self._lifecycle_callbacks = None
