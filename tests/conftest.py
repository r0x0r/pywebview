import pytest
from six.moves import reload_module


@pytest.fixture(autouse=True)
def reload_webview():
    import webview
    reload_module(webview)
