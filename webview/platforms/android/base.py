from threading import Semaphore

from android.activity import (  # noqa
    register_activity_lifecycle_callbacks,
    unregister_activity_lifecycle_callbacks,
)
from android.runnable import run_on_ui_thread  # noqa

from webview.platforms.android.event import EventDispatcher
from webview.platforms.android.jclass.view import Choreographer
from webview.platforms.android.jinterface.view import FrameCallback


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
        # p4a keeps every registered instance in a module-level set and only
        # drops it on unregister, so holding on to this one is what lets close()
        # detach it. Otherwise each new app would stack another live set of
        # callbacks pointing at the previous, already dismissed, view.
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
            unregister_activity_lifecycle_callbacks(self._lifecycle_callbacks)
            self._lifecycle_callbacks = None
