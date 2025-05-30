__all__ = ('Context',)

from jnius import JavaClass, MetaJavaClass, JavaStaticField


class Context(JavaClass, metaclass=MetaJavaClass):
    """
    Represents the Android Context Java class providing access to application-specific
    resources and services.

    This class serves as a bridge to interact with the Android framework and various
    system services provided by the Android operating system. It holds functionality
    for accessing application environments, managing resources, and invoking system:
    defined services.

    Attributes:
        __javaclass__ (str): The fully qualified Java class name representation of the Context class.
        DOWNLOAD_SERVICE (JavaStaticField): A static field representing the Java constant
            for the download service.
    """
    __javaclass__ = 'android/content/Context'
    DOWNLOAD_SERVICE = JavaStaticField('Ljava/lang/String;')
