__all__ = ('Environment',)

from jnius import JavaClass, MetaJavaClass, JavaStaticField


class Environment(JavaClass, metaclass=MetaJavaClass):
    """
    Represents the Android environment class for interacting with the external storage and system paths.

    This class provides access to system-defined constants and methods for
    interacting with the device's file and directory management environment.
    Acts as a proxy to the Android's Java environment class. Use its attributes
    and methods to access critical file paths or configurations within the
    Android operating system.

    Attributes:
        __javaclass__ (str): Represents the Java class path being bridged.
        DIRECTORY_DOWNLOADS (JavaStaticField): Static field representing the
            path for storing user downloads, defined in the Android
            environment.
    """
    __javaclass__ = 'android/os/Environment'
    DIRECTORY_DOWNLOADS = JavaStaticField('Ljava/lang/String;')
