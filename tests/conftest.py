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


# @pytest.fixture(autouse=True)
# def set_gui():
#     import os
#     os.environ['PYWEBVIEW_GUI'] = 'qt'
