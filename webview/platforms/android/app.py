from android.runnable import run_on_ui_thread  # noqa
from android.activity import _activity as act  # noqa
from webview.platforms.android.base import EventLoop
from webview.platforms.android.event import EventDispatcher


class App(EventDispatcher):
    # Return the current running App instance
    _running_app = None

    def __init__(self, **kwargs):
        App._running_app = self
        super().__init__(**kwargs)
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
        act.setContentView(root)

    def on_create(self, activity, saved_instance_state):
        """Event handler for the `on_create` event which is fired after
        initialization (after build() has been called) but before the
        application has started running.
        """

    def on_pause(self, activity):
        """Event handler called when Pause mode is requested"""

    def on_destroy(self, activity):
        """Event handler for the `on_destroy` event which is fired when the
        application has finished running (i.e. the window is about to be
        closed).
        """

    def on_resume(self, activity):
        pass

    def on_start(self, activity):
        pass

    def on_stop(self, activity):
        pass

    def run(self):
        self.build_view()
        self._eventloop.status = "created"
        self._eventloop.mainloop()

    @staticmethod
    def get_running_app():
        """Return the currently running application instance.
        """
        return App._running_app

    def pause(self):
        '''Pause the application.

        On Android set OS state to pause, Kivy app state follows.
        No functionality on other OS.
        .. versionadded:: 2.2.0
        '''
        act.moveTaskToBack(True)

    def stop(self):
        self.dispatch("on_destroy")
        self._eventloop.close()
        App._running_app = None
