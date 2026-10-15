class WebViewException(Exception):
    pass


class JavascriptException(Exception):
    pass


class ReentrantCallError(WebViewException, RuntimeError):
    """
    Raised when an API whose result is delivered asynchronously by the GUI thread is
    called from the GUI thread itself, e.g. from a closing, before_show or before_load
    handler. Waiting would deadlock, so the call raises instead.
    Subclasses RuntimeError, which some backends raised here previously.
    """
