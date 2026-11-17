class WebViewException(Exception):
    pass


class JavascriptException(Exception):
    pass


class SecurityException(WebViewException):
    """Raised when an operation is refused for security reasons."""
