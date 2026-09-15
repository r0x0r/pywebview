__all__ = ('Runnable',)

from jnius import PythonJavaClass, java_method


class Runnable(PythonJavaClass):
    """
    A Java `Runnable` that calls a Python function when the UI thread runs it.

    A single instance serves every posted call - see
    `webview.platforms.android.base.run_on_ui_thread`, which queues the work and
    posts this. The function therefore takes no arguments: it picks up what to
    run from that queue. Nothing is stored on the instance, so posts from
    different threads cannot overwrite each other's arguments.
    """

    __javacontext__ = 'app'
    __javainterfaces__ = ['java/lang/Runnable']

    def __init__(self, run):
        self.run_callback = run

    @java_method('()V')
    def run(self):
        self.run_callback()
