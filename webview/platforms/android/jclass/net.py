__all__ = ('Uri',)

from jnius import JavaClass, MetaJavaClass, JavaMethod, JavaStaticMethod


class Uri(JavaClass, metaclass=MetaJavaClass):
    """
    Represents a URI reference as defined in RFC 2396, composed of components such as
    scheme, authority, path, query, and fragment.

    The Uri class provides methods to work with uniform resource identifiers (URI). It
    facilitates parsing, retrieving specific parts of the URI, and performing a variety
    of URI-related manipulations. Typically used in Android development for handling
    URI-based resources.

    Attributes:
        __javaclass__ : str
            Specifies the associated Java class for this Python wrapper.
        parse : JavaMethod
            Represents the Java method 'parse' to convert a string to a Uri instance.
        getLastPathSegment : JavaMethod
            Represents the Java method 'getLastPathSegment' to retrieve the last
            segment of the URI's path.
    """
    __javaclass__ = 'android/net/Uri'
    parse = JavaStaticMethod('(Ljava/lang/String;)Landroid/net/Uri;')
    getLastPathSegment = JavaMethod('()Ljava/lang/String;')
