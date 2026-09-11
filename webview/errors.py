class WebViewException(Exception):
    pass


class JavascriptException(Exception):
    pass


class ReentrantCallError(WebViewException, RuntimeError):
    """
    Raised when a synchronous API that needs the GUI thread to deliver its
    result is called *from* the GUI thread itself.

    pywebview dispatches four events synchronously on the GUI thread so a
    handler can veto or mutate the outcome -- the ``should_lock=True`` events
    in ``webview/window.py``: ``closing``, ``before_show``, ``before_load`` and
    ``initialized``. Native callbacks (a XAML event handler, a GTK signal, a
    ``request_sent`` handler) run there too.

    While such a handler runs, it *is* the GUI thread. An API whose result is
    only produced asynchronously -- ``evaluate_js()``, ``get_cookies()``, a
    dialog -- has to wait for the GUI thread to deliver it, which can never
    happen while that same thread is blocked waiting. Blocking would deadlock
    the process permanently and uninterruptibly, so these APIs raise this
    instead.

    Subclasses ``RuntimeError`` for backwards compatibility with the plain
    ``RuntimeError`` these call sites used to raise.
    """
