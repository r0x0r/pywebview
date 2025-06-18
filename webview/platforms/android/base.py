from time import sleep

from webview.platforms.android.event import EventDispatcher
from android.activity import register_activity_lifecycle_callbacks, _activity as activity  # noqa


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
        while not self.quit and self.status == "created":
            sleep(1/60)  # Run at 60 FPS

    def close(self):
        self.quit = True
        self.status = "destroyed"
