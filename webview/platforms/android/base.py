from threading import Semaphore

from webview.platforms.android.event import EventDispatcher
from android.activity import register_activity_lifecycle_callbacks, _activity as activity  # noqa
from android.runnable import run_on_ui_thread  # noqa
from webview.platforms.android.jclass.view import Choreographer
from webview.platforms.android.jinterface.view import FrameCallback


class EventLoop(EventDispatcher):
    def __init__(self):
        super(EventLoop, self).__init__()
        from webview.platforms.android.app import App
        self.app = App.get_running_app()
        self.quit = False
        self.status = "idle"
        self.resumed = False
        self.destroyed = False
        self.paused = False
        register_activity_lifecycle_callbacks(
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
        while not self.quit and self.status == "created":
            def do_frame(_):
                lock.release()

            @run_on_ui_thread
            def post_frame():
                nonlocal choreographer, frame_callback

                if not choreographer:
                    choreographer = Choreographer.getInstance()
                if not frame_callback:
                    frame_callback = FrameCallback(do_frame)

                choreographer.postFrameCallback(frame_callback)

            lock = Semaphore(0)
            post_frame()
            lock.acquire()

    def close(self):
        self.quit = True
        self.status = "destroyed"
