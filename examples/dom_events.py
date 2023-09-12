"""This example demonstrates how to expose Python functions to the Javascript domain."""

import webview


def click_handler(e):
    print(e)


def expose(window):
    window.expose(click_handler)
    window.evaluate_js('document.querySelector("body").addEventListener("click", pywebview.api.click_handler)')

if __name__ == '__main__':
    window = webview.create_window(
        'DOM Event Example', html='<html><head></head><body><h1>Click me</h1></body></html>'
    )
    webview.start(expose, window)
