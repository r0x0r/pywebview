from android.runnable import run_on_ui_thread  # noqa
from android.activity import _activity as activity  # noqa
from webview.platforms.android.base import EventLoop
from webview.platforms.android.event import EventDispatcher


class App(EventDispatcher):
    # Return the current running App instance
    _running_app = None

    def __init__(self, **kwargs):
        App._running_app = self
        super().__init__(**kwargs)
        self.register_event_type("on_pause")
        self.register_event_type("on_create")
        self.register_event_type("on_destroy")
        self.register_event_type("on_resume")
        self._eventloop = EventLoop()

        #: The *root* widget returned by the :meth:`build_view`
        self.root = None

    def build_view(self):
        """Initializes the application; it will be called only once.
        If this method returns a widget (tree), it will be used as the root
        widget and added to the window.

        :return:
            None or a root :class:`~android.widget.RelativeLayout` instance
            if no self.root exists."""
        return self.root

    @run_on_ui_thread
    def set_content_view(self, root):
        activity.setContentView(root)

    def on_create(self):
        """Event handler for the `on_create` event which is fired after
        initialization (after build() has been called) but before the
        application has started running.
        """

    def on_pause(self):
        """Event handler called when Pause mode is requested"""

    def on_destroy(self):
        """Event handler for the `on_destroy` event which is fired when the
        application has finished running (i.e. the window is about to be
        closed).
        """

    def on_resume(self):
        pass

    def run(self):
        self.build_view()
        self._eventloop.status = "created"
        self.dispatch("on_create")
        self._eventloop.mainloop()

    @staticmethod
    def get_running_app():
        """Return the currently running application instance.
        """
        return App._running_app

    def stop(self):
        self.dispatch("on_destroy")
        self._eventloop.close()
        App._running_app = None
