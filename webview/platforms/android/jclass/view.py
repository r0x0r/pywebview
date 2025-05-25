from jnius import JavaClass, MetaJavaClass, JavaStaticField


class View(JavaClass, metaclass=MetaJavaClass):
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
    __javaclass__ = 'android/view/KeyEvent'
    KEYCODE_BACK = JavaStaticField('I')
