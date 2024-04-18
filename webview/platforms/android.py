import logging
import os
import json
from threading import Semaphore
from urllib.parse import urlparse

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock

from jnius import autoclass, cast, java_method, PythonJavaClass
from android.runnable import Runnable, run_on_ui_thread

from webview import _settings, settings
from webview.js.css import disable_text_select
from webview.util import create_cookie, js_bridge_call, inject_pywebview

AlertDialogBuilder = autoclass('android.app.AlertDialog$Builder')
AndroidString = autoclass('java.lang.String')
CookieManager = autoclass('android.webkit.CookieManager')
WebViewA = autoclass('android.webkit.WebView')
KeyEvent = autoclass('android.view.KeyEvent')
PyWebViewClient = autoclass('com.pywebview.PyWebViewClient')
PyWebChromeClient = autoclass('com.pywebview.PyWebChromeClient')
PyJavaScriptInterface = autoclass('com.pywebview.PyJavascriptInterface')
JavascriptValueCallback = autoclass('com.pywebview.JavascriptValueCallback')
activity = autoclass('org.kivy.android.PythonActivity').mActivity
Environment = autoclass('android.os.Environment')
DownloadManager = autoclass('android.app.DownloadManager')
DownloadManagerRequest = autoclass('android.app.DownloadManager$Request')
Uri = autoclass('android.net.Uri')
Context = autoclass('android.content.Context')


logger = logging.getLogger('pywebview')

renderer = 'android-webkit'
app = None


class DownloadListener(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['android/webkit/DownloadListener']

    @java_method('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;J)V')
    def onDownloadStart(self, url, userAgent, contentDisposition, mimetype, contentLength):
        context = activity.getApplicationContext()
        visibility = DownloadManagerRequest.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
        dir_type = Environment.DIRECTORY_DOWNLOADS
        uri = Uri.parse(url)
        filepath = uri.getLastPathSegment()
        request = DownloadManagerRequest(uri)
        request.setNotificationVisibility(visibility)
        request.setDestinationInExternalFilesDir(context, dir_type, filepath)
        dm = cast(DownloadManager, activity.getSystemService(Context.DOWNLOAD_SERVICE))
        dm.enqueue(request)


class KeyListener(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['android/view/View$OnKeyListener']

    def __init__(self, listener):
        super().__init__()
        self.listener = listener

    @java_method('(Landroid/view/View;ILandroid/view/KeyEvent;)Z')
    def onKey(self, v, key_code, event):
        if key_code == KeyEvent.KEYCODE_BACK:
            return self.listener()


class EventCallbackWrapper(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['com/pywebview/EventCallbackWrapper']

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Ljava/lang/String;Ljava/lang/String;)V')
    def callback(self, event, data):
        if self.callback:
            self.callback(event, data)


class JsApiCallbackWrapper(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['com/pywebview/JsApiCallbackWrapper']

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
    def callback(self, func, params, id):
        if self.callback:
            Runnable(self.callback)(func, params, id)


def run_ui_thread(f, *args, **kwargs):
    Runnable(f)(args, kwargs)


class BrowserView(Widget):
    def __init__(self, window, **kwargs):
        self.window = window
        self.webview = None
        self.dialog = None
        super(BrowserView, self).__init__(**kwargs)
        Clock.schedule_once(lambda dt: run_ui_thread(self.create_webview), 0)

    def create_webview(self, *args):
        def js_api_handler(func, params, id):
            js_bridge_call(self.window, func, json.loads(params), id)

        def loaded_callback(event, data):
            self.window.events.loaded.set()

        def chrome_callback(event, data):
            print(event, data)

        def webview_callback(event, data):
            if event == 'onPageFinished':
                if not self.window.text_select:
                    self.webview.evaluateJavascript(disable_text_select, None)

                value_callback = JavascriptValueCallback()
                value_callback.setCallback(EventCallbackWrapper(loaded_callback))
                self.webview.evaluateJavascript(inject_pywebview(self.window, renderer), value_callback)

                if not _settings['private_mode']:
                    CookieManager.getInstance().setAcceptCookie(True)
                    CookieManager.getInstance().acceptCookie()
                    CookieManager.getInstance().flush()
                else:
                    CookieManager.getInstance().setAcceptCookie(False)

            elif event == 'onCookiesReceived':
                cookies = json.loads(data)
                url = cookies['url']

                if url in self._cookies:
                    self._cookies[url] = list(set(self._cookies[url] + cookies['cookies']))
                else:
                    self._cookies[url] = cookies['cookies']

        self._cookies = {}
        self.webview = WebViewA(activity)
        webview_settings = self.webview.getSettings()
        webview_settings.setAllowFileAccessFromFileURLs(True)
        webview_settings.setJavaScriptEnabled(True)
        webview_settings.setUseWideViewPort(False)
        webview_settings.setLoadWithOverviewMode(True)
        webview_settings.setSupportZoom(self.window.zoomable)
        webview_settings.setBuiltInZoomControls(False)
        webview_settings.setDomStorageEnabled(not _settings['private_mode'])

        if _settings['user_agent']:
            webview_settings.setUserAgentString(_settings['user_agent'])

        self._webview_callback_wrapper = EventCallbackWrapper(webview_callback)
        webview_client = PyWebViewClient()
        webview_client.setCallback(self._webview_callback_wrapper, _settings['ssl'])
        self.webview.setWebViewClient(webview_client)

        self._chrome_callback_wrapper = EventCallbackWrapper(chrome_callback)
        chrome_client = PyWebChromeClient()
        chrome_client.setCallback(self._chrome_callback_wrapper)
        self.webview.setWebChromeClient(chrome_client)

        self._js_api_callback_wrapper = JsApiCallbackWrapper(js_api_handler)
        js_interface = PyJavaScriptInterface()
        js_interface.setCallback(self._js_api_callback_wrapper)
        self.webview.addJavascriptInterface(js_interface, 'external')

        activity.setContentView(self.webview)

        if settings['ALLOW_DOWNLOADS']:
            self.webview.setDownloadListener(DownloadListener())

        self.webview.setOnKeyListener(KeyListener(self._back_pressed))

        if self.window.real_url:
            self.webview.loadUrl(self.window.real_url)
        elif self.window.html:
            self.webview.loadDataWithBaseURL(None, self.window.html, 'text/html', 'UTF-8', None)

        self.window.events.shown.set()

    def dismiss(self):
        if _settings['private_mode']:
            self.webview.clearHistory()
            self.webview.clearCache(True)
            self.webview.clearFormData()

        self.webview.destroy()
        self.layout = None
        self.webview = None
        app.stop()

    def _quit_confirmation(self):
        def cancel(dialog, which):
            self.dialog = None

        def quit(dialog, which):
            self.window.closed.set()
            self.dialog = None
            app.stop()

        if self.dialog:
            return

        context = self.webview.getContext()
        message = AndroidString(self.window.localization['global.quitConfirmation'])
        quit_msg = AndroidString(self.window.localization['global.quit'])
        cancel_msg = AndroidString(self.window.localization['global.cancel'])

        self.dialog = AlertDialogBuilder(context) \
            .setMessage(message) \
            .setPositiveButton(quit_msg, quit) \
            .setNegativeButton(cancel_msg, cancel) \
            .setOnCancelListener(cancel) \
            .show()

    def _back_pressed(self):
        if self.webview.canGoBack():
            self.webview.goBack()
            return
        should_cancel = self.window.closing.set()

        if should_cancel:
            return

        if self.window.confirm_close:
            self._quit_confirmation()
        else:
            app.pause()
            self.window.closed.set()


        return True

class AndroidApp(App):
    def __init__(self, window):
        self.window = window
        self.first_show = True
        super().__init__()

    def build(self):
        self.view = BrowserView(self.window)
        return self.view

    def on_pause(self):
        def _pause():
            self.view.webview.pauseTimers()
            self.view.webview.onPause()

        logger.debug('pausing initiated')

        # on_pause triggers on first show for some reason, so we need to ignore it
        if self.view.webview and not self.first_show:
            logger.debug('pausing')
            Runnable(_pause)()

        self.first_show = False

        return True

    def on_resume(self):
        def _resume():
            logger.debug('resuming')
            self.view.webview.onResume()
            self.view.webview.resumeTimers()

        if self.view.webview:
            Runnable(_resume)()

    def on_stop(self):
        return True


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, _):
    logger.warning('Creating file dialogs is not supported on Android')


def create_window(window):
    global app

    if app:
        logger.error('Multiple windows are not supported on Android')
        return

    app = AndroidApp(window)
    app.run()


def setup_app():
    pass


@run_on_ui_thread
def load_url(url, _):
    app.window.events.loaded.clear()
    app.view._cookies = {}
    app.view.webview.loadUrl(url)


@run_on_ui_thread
def load_html(html_content, base_uri, _):
    app.window.events.loaded.clear()
    app.view._cookies = {}
    app.view.webview.loadDataWithBaseURL(base_uri, html_content, 'text/html', 'UTF-8', None)


def evaluate_js(js_code, unique_id):
    def callback(event, result):
        nonlocal js_result
        result = json.loads(result)
        js_result = json.loads(result) if result else None
        lock.release()

    def _evaluate_js():
        callback_wrapper = EventCallbackWrapper(callback)
        value_callback = JavascriptValueCallback()
        value_callback.setCallback(callback_wrapper)
        app.view.webview.evaluateJavascript(js_code, value_callback)

    lock = Semaphore(0)
    js_result = None

    Runnable(_evaluate_js)()
    lock.acquire()
    return js_result

def clear_cookies(_):
    def _cookies():
        CookieManager.getInstance().removeAllCookies(None)

    Runnable(_cookies)()

def get_cookies(_):
    def _cookies():
        nonlocal cookies

        raw_cookies = app.view._cookies
        full_url = app.view.webview.getUrl()
        url = urlparse(full_url)
        url = f'{url.scheme}://{url.netloc}'

        if url in raw_cookies:
            cookies = [ create_cookie(c) for c in raw_cookies[url] ]

        for c in {x for v in raw_cookies.values() for x in v}:
            cookie = create_cookie(c)
            domain = next(iter(cookie.values())).get('domain')

            if not domain:
                continue

            if domain.startswith('.') and url.endswith(domain.lstrip('.')) or not domain.startswith('.') and url == domain:
                cookies.append(cookie)

        lock.release()

    cookies = []
    lock = Semaphore(0)
    Runnable(_cookies)()
    lock.acquire()

    return cookies

@run_on_ui_thread
def get_current_url(_):
    return app.view.getUrl()

def get_screens():
    return []


@run_on_ui_thread
def get_size(_):
    return (app.view.width, app.view.height)


def get_position(_):
    return (0, 0)


def show(_):
    logger.warning('Showing window is not supported on Android')


def hide(_):
    app.pause()


def minimize(_):
    app.pause()


def move(_):
    logger.warning('Moving window is not supported on Android')


def restore(_):
    logger.warning('Restoring window is not supported on Android')


def resize(width, height, _, fix_point):
    logger.warning('Resizing window is not supported on Android')


def destroy_window():
    app.stop()


def set_title(title, _):
    logger.warning('Changing app title is not supported on Android')


def set_on_top(_, on_top):
    logger.warning('Always on top mode is not supported on Android')


def toggle_fullscreen(_):
    logger.warning('Fullscreen mode is not supported on Android')


def add_tls_cert(certfile):
    pass