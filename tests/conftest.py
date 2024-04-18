import pytest
from importlib import reload

@pytest.fixture(autouse=True)
def reload_webview():
    import webview

    reload(webview)
