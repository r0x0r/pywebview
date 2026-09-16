__all__ = ('Runnable',)

from jnius import PythonJavaClass, java_method


class Runnable(PythonJavaClass):
    """
    A Java `Runnable` that calls a Python function when the UI thread runs it.

    A single instance serves every posted call, so `run` takes no arguments and
    picks up the work from the queue in
    `webview.platforms.android.base.run_on_ui_thread` instead.
    """

    __javacontext__ = 'app'
    __javainterfaces__ = ['java/lang/Runnable']

    def __init__(self, run):
        self.run_callback = run

    @java_method('()V')
    def run(self):
        self.run_callback()
