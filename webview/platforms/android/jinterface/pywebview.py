__all__ = ('EventCallbackWrapper', 'JsApiCallbackWrapper', 'RequestInterceptor')

from jnius import PythonJavaClass, java_method


class EventCallbackWrapper(PythonJavaClass):
    """
    Represents a wrapper for event callbacks between Python and Java.

    This class enables interaction between Python and Java by implementing
    a Java interface and providing a callback mechanism. The purpose is to
    allow Python to respond to events triggered from the Java side by
    passing the event and related data.

    Attributes:
    callback (Callable[[str, str], None]): A callable function that handles
    an event and its associated data.

    Methods:
    callback(event: str, data: str): Calls the provided callback function
    with the given event and data.
    """
    __javacontext__ = 'app'
    __javainterfaces__ = ['com/pywebview/EventCallbackWrapper']

    def __init__(self, callback):
        self.callback_wrapper = callback

    @java_method('(Ljava/lang/String;Ljava/lang/String;)V')
    def callback(self, event, data):
        self.callback_wrapper(event, data)


class JsApiCallbackWrapper(PythonJavaClass):
    """
    Wrapper class for JavaScript API callbacks.

    This class serves as a bridge between a Python application and a Java
    environment, enabling communication through JavaScript API callback functionality.
    It implements the `JsApiCallbackWrapper` interface and is designed specifically
    for use with webview integration.

    Attributes:
    callback (Callable): A Python callable that gets executed when the callback
    method is triggered. The callable should accept three arguments.

    """
    __javacontext__ = 'app'
    __javainterfaces__ = ['com/pywebview/JsApiCallbackWrapper']

    def __init__(self, callback):
        self.callback_wrapper = callback

    @java_method('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
    def callback(self, func, params, id):
        self.callback_wrapper(func, params, id)


class RequestInterceptor(PythonJavaClass):
    """
    Represents a class for intercepting web view requests and responses.

    This class provides a mechanism to handle events during web view
    requests and responses by allowing custom callback functions to be
    invoked. It acts as a bridge between Python and Java for facilitating
    interception of web-related actions within a web view environment.

    Attributes:
        on_request (Callable[[str, str, str], str]): Callback function that gets
            invoked when a web request is intercepted. The callback function should
            accept the request URL, HTTP method, and headers in JSON format, and it
            should return a string.
        on_response (Callable[[str, int, str], None]): Callback function that gets
            invoked when a web response is intercepted. The callback function should
            accept the response URL, HTTP status code, and headers in JSON format.

    """
    __javacontext__ = 'app'
    __javainterfaces__ = ['com/pywebview/WebViewRequestInterceptor']

    def __init__(self, on_request, on_response):
        self.on_request = on_request
        self.on_response = on_response

    @java_method('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;')
    def onRequest(self, url: str, method: str, headers_json: str):
        return self.on_request(url, method, headers_json)

    @java_method('(Ljava/lang/String;ILjava/lang/String;)V')
    def onResponse(self, url: str, status_code: int, headers_json: str):
        self.on_response(url, status_code, headers_json)
