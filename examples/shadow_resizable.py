"""Test: frameless + shadow + resizable window."""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

for _m in list(sys.modules):
    if _m == 'webview' or _m.startswith('webview.'):
        del sys.modules[_m]

import webview

_RED_HTML = '''
<!DOCTYPE html>
<html>
<head>
<style>
  html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background: red;
  }
</style>
</head>
<body></body>
</html>
'''

if __name__ == '__main__':
    webview.create_window(
        'Frameless + Shadow + Resizable Test',
        html=_RED_HTML,
        frameless=True,
        shadow=True,
        resizable=True,
        easy_drag=True,
        width=800,
        height=600,
        min_size=(300, 200),
        background_color='#FF0000',
    )
    webview.start()
