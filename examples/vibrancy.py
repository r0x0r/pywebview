'''
Description: 
Author: chenebenzheng
Date: 2022-08-16 15:59:13
LastEditTime: 2022-08-16 18:07:25
LastEditors: chenebenzheng
Reference: 
'''
import webview
import threading
import time

"""
This example demonstrates how to set vibrancy (macos).
window set transparent and html set background to transparent
"""

def load_css(window):
    window.load_css('body { background: transparent !important; }')


if __name__ == '__main__':
    window = webview.create_window('set vibrancy example', 
    'https://pywebview.flowrl.com/hello',
     transparent=True,
     vibrancy=True)
    webview.start(load_css, window)