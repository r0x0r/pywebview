from jnius import JavaClass, MetaJavaClass, JavaMethod, JavaStaticMethod, JavaMultipleMethod


class PyWebViewClient(JavaClass, metaclass=MetaJavaClass):
    """
    Represents a custom WebView client implementation for handling webview events in an Android environment.

    This class is a Python binding to a Java class that extends functionalities for handling
    web-related events in a WebView component. It is typically used in conjunction with the pywebview library
    to manage and interact with web pages loaded within the Android WebView context. The class provides methods
    for setting callback handlers, managing page load events, handling SSL errors, and executing or intercepting
    resource requests.

    Attributes:
    __javaclass__: str
        Fully qualified name of the Java class represented by this Python wrapper.

    Methods:
    setCallback(callback_wrapper: 'JavaObject', flag: bool) -> None
        Configures callback handlers for webview events. The method associates an instance
        of a callback wrapper with the webview actions.

    onPageFinished(webview: 'JavaObject', url: str) -> None
        Invoked when the page finishes loading in the WebView. Provides the URL of the loaded page.

    onReceivedSslError(webview: 'JavaObject', ssl_error_handler: 'JavaObject', ssl_error: 'JavaObject') -> None
        Handles SSL error events triggered by the WebView during loading. Allows managing or overriding
        the SSL certificate behavior.

    shouldInterceptRequest(webview: 'JavaObject', web_resource_request: 'JavaObject') -> 'JavaObject'
        Intercepts requests made within the WebView. Allows modification or substitution of
        the response returned for a given resource request.

    executeRequest(url: str) -> 'JavaObject'
        Processes and retrieves responses for specific resources manually. This method can
        be used to override or provide custom responses for URL requests.
    """
    __javaclass__ = 'com/pywebview/PyWebViewClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;Z)V')
    onPageFinished = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;)V')
    onReceivedSslError = JavaMethod('(Landroid/webkit/WebView;Landroid.webkit.SslErrorHandler;'
                                    'Landroid.net.http.SslError;)V')
    shouldInterceptRequest = JavaMethod('(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)'
                                        'Landroid.webkit.WebResourceResponse;')
    executeRequest = JavaMethod('(Ljava/lang/String;)Landroid.webkit.WebResourceResponse;')


class PyWebChromeClient(JavaClass, metaclass=MetaJavaClass):
    """
    Handles communication with the WebView's JavaScript environment.

    The PyWebChromeClient class acts as a bridge between JavaScript running in a WebView
    and the Python environment. By defining methods that handle JavaScript interactions,
    such as alert dialogs and confirmation dialogs, this class provides mechanisms
    to integrate JavaScript behaviors into Python-based applications.

    Attributes:
        __javaclass__: The fully qualified class name of the Java class that this Python
                       bridge wraps for interaction.

    Methods:
        setCallback: Sets the callback mechanism for handling JavaScript events. Takes an
                     EventCallbackWrapper as an argument.
        onJsAlert: Handles JavaScript alert dialogs presented within a WebView. It processes
                   the dialog content and determines whether the alert is handled in
                   the Python environment.
        onJsConfirm: Handles JavaScript confirmation dialogs within a WebView, allowing the
                     Python application to process the user's response to the dialog.
    """
    __javaclass__ = 'com/pywebview/PyWebChromeClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;)V')
    onJsAlert = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;Ljava/lang/String;'
                           'android.webkit.JsResult;)Z')
    onJsConfirm = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;Ljava/lang/String;'
                             'android.webkit.JsResult;)Z')


class PyJavascriptInterface(JavaClass, metaclass=MetaJavaClass):
    """
    Interface that acts as a bridge between Python and the JavaScript context.

    This class provides methods to set a callback and to handle JavaScript
    calls by interfacing with the Java-based functionality. It enables
    interactions between Python code and JavaScript running on a web view or
    similar component by defining Java methods that can be invoked from
    JavaScript.

    Attributes:
        __javaclass__ (str): Represents the Java class path of the associated
            Java implementation.

    Methods:
        setCallback: Registers a JavaScript API callback wrapper to handle
            responses from JavaScript to Python.
        call: Executes a specified JavaScript function with provided context
            and arguments.
    """
    __javaclass__ = 'com/pywebview/PyJavascriptInterface'
    setCallback = JavaMethod('(Lcom/pywebview/JsApiCallbackWrapper;)V')
    call = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')


class CookieManager(JavaClass, metaclass=MetaJavaClass):
    """
    Manages browser cookies for the WebView component and provides methods for
    cookie handling.

    The CookieManager class offers a variety of methods to control HTTP cookie
    management within a WebView environment. Using this class, you can query,
    set, accept, and delete cookies, as well as enable or disable the acceptance
    of third-party or file-scheme cookies. Cookie management features are essential
    for maintaining session persistence and enforcing privacy policies in web views
    embedded within Android applications.

    Attributes:
        __javaclass__ (str): Specifies the underlying Java class representation
            of the `android.webkit.CookieManager`.

    Methods:
        getInstance(): Retrieves the singleton instance of the CookieManager.

        setAcceptCookie(accept: bool): Sets whether the WebView should accept
            cookies globally.

        acceptCookie(accept: bool): Checks whether the web environment accepts cookies.

        setAcceptThirdPartyCookies(view, accept: bool): Determines whether the
            specified WebView should accept third-party cookies.

        acceptThirdPartyCookies(view): Indicates whether the given WebView accepts
            third-party cookies.

        setCookie(url: str, value: str, callback: Optional = None): Sets a cookie
            for the specified URL, optionally performing an action asynchronously
            upon completion.

        getCookie(url: str): Retrieves the cookie(s) associated with the specified
            URL.

        removeSessionCookie(): Removes all session cookies synchronously.

        removeSessionCookies(callback): Removes all session cookies asynchronously,
            triggering the provided ValueCallback upon completion.

        removeAllCookie(): Deletes all cookies synchronously.

        removeAllCookies(callback): Deletes all cookies asynchronously, using the
            provided ValueCallback to notify when the task is completed.

        hasCookies(): Indicates whether any cookies are stored.

        removeExpiredCookie(): Removes cookies that are no longer valid based on
            their expiration attributes.

        flush(): Forces synchronous writing of the cookie state to storage.

        allowFileSchemeCookies(): Checks if cookies for file-scheme URLs are
            accepted.

        setAcceptFileSchemeCookies(accept: bool): Enables or disables the
            acceptance of cookies for file-scheme URLs.
    """
    __javaclass__ = 'android/webkit/CookieManager'

    getInstance = JavaStaticMethod('()Landroid/webkit/CookieManager;')
    setAcceptCookie = JavaMethod('(Z)V')
    acceptCookie = JavaMethod('(Z)V')
    setAcceptThirdPartyCookies = JavaMethod('(Landroid/webkit/WebView;Z)V')
    acceptThirdPartyCookies = JavaMethod('(Landroid/webkit/WebView;)Z')
    setCookie = JavaMultipleMethod([
        ('(Ljava/lang/String;Ljava/lang/String;)V', False, False),
        ('(Ljava/lang/String;Ljava/lang/String;Landroid/webkit/ValueCallback;)V', False, False)
    ])
    getCookie = JavaMethod('(Ljava/lang/String;)Ljava/lang/String;')
    removeSessionCookie = JavaMethod('()V')
    removeSessionCookies = JavaMethod('(Landroid/webkit/ValueCallback;)V')
    removeAllCookie = JavaMethod('()V')
    removeAllCookies = JavaMethod('(Landroid/webkit/ValueCallback;)V')
    hasCookies = JavaMethod('()Z')
    removeExpiredCookie = JavaMethod('()V')
    flush = JavaMethod('()V')
    allowFileSchemeCookies = JavaStaticMethod('()Z')
    setAcceptFileSchemeCookies = JavaStaticMethod('(Z)V')
