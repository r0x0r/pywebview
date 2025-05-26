from webview.platforms.android.event import EventDispatcher
from android.activity import _activity as activity  # noqa


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

    def mainloop(self):
        while not self.quit and self.status == "created":
            self.poll()

    def poll(self):
        if activity.isResumed() and not self.resumed:
            self.app.dispatch("on_resume")
            self.resumed = activity.resumed
            self.paused = False

        if activity.isDestroyed() and not self.destroyed:
            self.app.dispatch("on_destroy")
            self.destroyed = activity.destroyed
            self.resumed = False

        if not activity.hasWindowFocus() and not self.paused:
            self.app.dispatch("on_pause")
            self.paused = True
            self.resumed = False

    def close(self):
        self.quit = True
        self.status = "destroyed"
