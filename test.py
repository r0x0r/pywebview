import os
from time import sleep
from tests.util import run_test, assert_js
import webview
import pyscreenshot as ImageGrab


def test_start():
    api = Api()
    window = webview.create_window('Relative URL test', 'assets/test.html', js_api=api)
    run_test(webview, window, assert_func, start_args={'block' : False})
    print('noblock/multiprocessing test is working.')
    sleep(1)
    # grab fullscreen
    im = ImageGrab.grab()

    # save image file
    im.save('test.png')


def assert_func(window):
    sleep(1)
    # grab fullscreen
    im = ImageGrab.grab()

    # save image file
    im.save('alert.png')
