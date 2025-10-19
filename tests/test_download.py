import time

import pytest

import webview

from .util import run_test

html = """
<html>
  <body>
    <button id="start_download" onclick="click_handler()">Click me!</button>
  </body>
  <script>
    function click_handler(){
      const a = document.createElement('a'); // Create "a" element
      const blob = new Blob(["Hello, World!"], { type: "text/plain" });
      const url = URL.createObjectURL(blob); // Create an object URL from blob
      a.setAttribute('href', url); // Set "a" element link
      a.setAttribute('download', 'test_download.txt');
      a.click(); // Start downloading
      a.remove();
    }

    function verify_result(){
        return confirm("Did the system prompt you for a download with name test_download.txt or download a file by that name? OK for yes, Cancel for no");
    }

    function checkFocus() {
       return document.hasFocus();
    }
  </script>
</html>
"""


@pytest.fixture
def window():
    return webview.create_window('Download test', html=html)


# skip this test by default since it's a manual test that requires user interaction
@pytest.mark.skip
def test_download_attribute(window):
    webview.settings['ALLOW_DOWNLOADS'] = True
    run_test(webview, window, download_test)


def get_result():
    res = input(
        'Did the system prompt you for a download with name test_download.txt or download a file by that name? Y/N'
    ).upper()
    return res == 'Y'


def download_test(window):
    # this should not cause the browser to navigate away but instead should trigger a download
    # since the type is text the browser should support it and if it navigates to it it will display it instead
    window.evaluate_js("document.getElementById('start_download').click();")
    time.sleep(0.5)  # make sure it has executed

    # if it loaded on the page and navigated away then it will fail this
    elements = window.dom.get_elements('#start_download')
    assert len(elements) == 1

    # wait for download prompt to be dismissed and focus to come back to window
    while not window.evaluate_js('checkFocus()'):
        time.sleep(0.5)

    # ask user if the test passed
    assert window.evaluate_js('verify_result();')
