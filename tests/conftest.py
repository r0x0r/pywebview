import pytest
from importlib import reload

@pytest.fixture(autouse=True)
def reload_webview():
    import webview

    reload(webview)

@pytest.fixture(autouse=True)
def set_env():
    import os

    os.environ['PYWEBVIEW_TEST'] = 'true'


# @pytest.fixture(autouse=True)
# def set_gui():
#     import os
#     os.environ['PYWEBVIEW_GUI'] = 'qt'