import pytest
import threading
from .util import run_test, get_test_name
import webview


html = """
  <html>
    <body>
      <h1 id="heading">Heading</h1>
      <div class="content">Content 1</div>
      <div class="content">Content 2</div>
    </body>
  </html>
"""

@pytest.fixture
def window():
    return webview.create_window('Get elements test', html=html)


def test_single(window):
    run_test(webview, window, single_test)


def test_multiple(window):
    run_test(webview, window, multiple_test)


def test_none(window):
    run_test(webview, window, none_test)


def single_test(window):
    try:
        elements = window.get_elements('#heading')
        assert len(elements) == 1
        assert elements[0]['innerHTML'] == 'Heading'
    except NotImplementedError:
        pass


def multiple_test(window):
    try:
        elements = window.get_elements('.content')
        assert len(elements) == 2
        assert elements[0]['innerHTML'] == 'Content 1'
        assert elements[1]['innerHTML'] == 'Content 2'
    except NotImplementedError:
        pass


def none_test(window):
    try:
        elements = window.get_elements('.adgdfg')
        assert len(elements) == 0
    except NotImplementedError:
        pass
