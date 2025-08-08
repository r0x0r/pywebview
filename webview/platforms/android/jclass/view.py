__all__ = ('View', 'KeyEvent', 'Choreographer')

from jnius import JavaClass, MetaJavaClass, JavaStaticField, JavaMethod, JavaMultipleMethod, JavaStaticMethod


class View(JavaClass, metaclass=MetaJavaClass):
    """
    Represents an Android view class with constants for system UI visibility flags.

    Provides direct references to various system UI visibility constants, which
    are used to control the appearance of the system user interface elements
    such as the status bar, navigation bar, and fullscreen modes. This class
    serves as a bridge to work with Java's Android View API in Python through
    a metaclass-based approach.

    Attributes
    ----------
    __javaclass__ : str
        The name of the corresponding Java class used for this bridge.
    SYSTEM_UI_FLAG_FULLSCREEN : JavaStaticField
        Constant for enabling fullscreen mode in the system UI.
    SYSTEM_UI_FLAG_HIDE_NAVIGATION : JavaStaticField
        Constant for hiding the navigation bar in the system UI.
    SYSTEM_UI_FLAG_IMMERSIVE : JavaStaticField
        Constant for enabling immersive mode.
    SYSTEM_UI_FLAG_IMMERSIVE_STICKY : JavaStaticField
        Constant for enabling sticky immersive mode.
    SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN : JavaStaticField
        Constant for making the layout occupy the fullscreen area.
    SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION : JavaStaticField
        Constant for making the layout extend under the navigation bar.
    SYSTEM_UI_FLAG_LAYOUT_STABLE : JavaStaticField
        Constant for preventing layout changes when the system UI
        visibility changes.
    SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR : JavaStaticField
        Constant for enabling light navigation bar mode.
    SYSTEM_UI_FLAG_LIGHT_STATUS_BAR : JavaStaticField
        Constant for enabling light status bar mode.
    SYSTEM_UI_FLAG_LOW_PROFILE : JavaStaticField
        Constant for enabling low-profile mode for system UI.
    SYSTEM_UI_FLAG_VISIBLE : JavaStaticField
        Constant for ensuring the system UI is visible.
    SYSTEM_UI_LAYOUT_FLAGS : JavaStaticField
        Combined constant for specifying multiple layout-related flags.
    """
    __javaclass__ = 'android/view/View'
    SYSTEM_UI_FLAG_FULLSCREEN = JavaStaticField('I')
    SYSTEM_UI_FLAG_HIDE_NAVIGATION = JavaStaticField('I')
    SYSTEM_UI_FLAG_IMMERSIVE = JavaStaticField('I')
    SYSTEM_UI_FLAG_IMMERSIVE_STICKY = JavaStaticField('I')
    SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN = JavaStaticField('I')
    SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION = JavaStaticField('I')
    SYSTEM_UI_FLAG_LAYOUT_STABLE = JavaStaticField('I')
    SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR = JavaStaticField('I')
    SYSTEM_UI_FLAG_LIGHT_STATUS_BAR = JavaStaticField('I')
    SYSTEM_UI_FLAG_LOW_PROFILE = JavaStaticField('I')
    SYSTEM_UI_FLAG_VISIBLE = JavaStaticField('I')
    SYSTEM_UI_LAYOUT_FLAGS = JavaStaticField('I')


class KeyEvent(JavaClass, metaclass=MetaJavaClass):
    """
    Represents a wrapper for the Android KeyEvent class.

    This class serves as a Python representation of the Android KeyEvent Java class, providing access
    to Java static fields, and facilitating interaction with Android key event constants and properties.

    Attributes:
    KEYCODE_BACK : int
        Static field representing the key code for the "Back" button in Android.
    """
    __javaclass__ = 'android/view/KeyEvent'
    KEYCODE_BACK = JavaStaticField('I')
    ACTION_DOWN = JavaStaticField('I')

    getAction = JavaMethod('()I')


class Choreographer(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'android/view/Choreographer'
    getInstance = JavaStaticMethod('()Landroid/view/Choreographer;')
    postFrameCallback = JavaMethod('(Landroid/view/Choreographer$FrameCallback;)V')
    removeFrameCallback = JavaMethod('(Landroid/view/Choreographer$FrameCallback;)V')
