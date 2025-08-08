"""
This package will help reduce overhead startup time of pywebview android application
on android. It will be responsible for defining android and api signature to reduce
the over head cost of pyjnius finding all signatures by itself.
"""
from webview.platforms.android.jclass.app import DownloadManagerRequest, AlertDialogBuilder
from webview.platforms.android.jclass.content import Context
from webview.platforms.android.jclass.net import Uri
from webview.platforms.android.jclass.os import Environment
from webview.platforms.android.jclass.view import View, KeyEvent
from webview.platforms.android.jclass.webkit import (
    WebView,
    CookieManager,
    PyJavascriptInterface,
    PyWebViewClient,
    PyWebChromeClient,
)
