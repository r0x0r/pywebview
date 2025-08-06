__all__ = ('KeyListener', 'FrameCallback')

from jnius import PythonJavaClass, java_method


class KeyListener(PythonJavaClass):
    """
    Represents a Python implementation of an Android `OnKeyListener`.

    This class provides an interface for handling key events in an Android environment
    using Python. It acts as a bridge between Python and the Android KeyListener
    interface. The primary purpose is to allow the execution of a Python function
    each time a key event is triggered.

    The class is structured to integrate with the Java ecosystem and is instantiated
    with a listener function defined in Python. This function enables the handling of
    key events by passing relevant details to it, empowering flexible event handling
    in a Pythonic manner.

    Attributes:
    listener (Callable): A Python callable function that will be triggered
        when a key event occurs. The function is expected to have three parameters:
        - v (android.view.View): The view that triggered the key event.
        - key_code (int): The key code of the key event.
        - event (android.view.KeyEvent): The Android KeyEvent object.
    """
    __javacontext__ = 'app'
    __javainterfaces__ = ['android/view/View$OnKeyListener']

    def __init__(self, listener):
        self.listener = listener

    @java_method('(Landroid/view/View;ILandroid/view/KeyEvent;)Z')
    def onKey(self, v, key_code, event):
        return self.listener(v, key_code, event)


class FrameCallback(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['android/view/Choreographer$FrameCallback']

    def __init__(self, do_frame):
        self.do_frame = do_frame

    @java_method('(J)V')
    def doFrame(self, frame_time_nanos):
        self.do_frame(frame_time_nanos)
