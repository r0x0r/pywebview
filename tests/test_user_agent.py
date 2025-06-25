import os
import pytest

import webview

from .util import run_test

@pytest.fixture
def window():
    return webview.create_window('User Agent Test', html='<html><body>User Agent Test</body></html>')

# This test is skipped on AppVeyor because it does not support changing the user agent for some reason.
@pytest.mark.skip #if(os.environ.get('APPVEYOR') == 'true', reason="Skip on AppVeyor")
def test_user_agent(window):
    run_test(webview, window, user_agent_test, start_args={'user_agent': 'Custom user agent'})

def user_agent_test(window):
    result = window.evaluate_js('navigator.userAgent')
    assert isinstance(result, str)
    assert result == 'Custom user agent'
