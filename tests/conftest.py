import logging
from importlib import reload

import pytest


@pytest.fixture(autouse=True)
def reload_webview():
    import webview
    from webview import http

    reload(webview)
    reload(http)


@pytest.fixture(autouse=True)
def set_env():
    import os

    os.environ['PYWEBVIEW_TEST'] = 'true'


@pytest.fixture
def quiet_console_log():
    """Mute pywebview's console handler for tests that log errors on purpose.

    CI runs pytest with -s, so the handler would print those tracebacks. Pytest still captures
    the records and shows them for a failing test, and caplog keeps working.
    """
    handlers = list(logging.getLogger('pywebview').handlers)
    levels = [handler.level for handler in handlers]
    for handler in handlers:
        handler.setLevel(logging.CRITICAL + 1)
    yield
    for handler, level in zip(handlers, levels):
        handler.setLevel(level)


# @pytest.fixture(autouse=True)
# def set_gui():
#     import os
#     os.environ['PYWEBVIEW_GUI'] = 'qt'
