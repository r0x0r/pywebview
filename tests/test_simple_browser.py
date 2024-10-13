import webview

from .util import run_test
from logging import getLogger
logger = getLogger('pywebview')
logger.setLevel('DEBUG')

def test_simple_browser():
    logger.info('test_simple_browser')
    window = webview.create_window('Simple browser test', 'https://www.example.org')
    logger.info('window created')

    run_test(webview, window)
