import os
import json
os.environ['CLASSPATH'] = os.path.join(os.path.dirname(__file__), '..', 'lib')

from threading import Semaphore

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock

from jnius import autoclass, cast, java_method, PythonJavaClass
from android.runnable import Runnable, run_on_ui_thread

from webview import _settings
from webview.js.css import disable_text_select
from webview.util import DEFAULT_HTML, create_cookie, js_bridge_call, inject_pywebview

CookieManager = autoclass('android.webkit.CookieManager')
WebViewA = autoclass('android.webkit.WebView')
JavaObject = autoclass('java.lang.Object')
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


renderer = 'android-webkit'


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
        request.setDestinationInExternalFilesDir(context,dir_type, filepath)
        dm = cast(DownloadManager, activity.getSystemService(Context.DOWNLOAD_SERVICE))
        dm.enqueue(request)


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
        print('JS API CALLBACK')
        print(func, params, id)
        if self.callback:
            self.callback(func, params, id)


def run_ui_thread(f, *args, **kwargs):
    Runnable(f)(args, kwargs)


class BrowserView(Widget):
    def __init__(self, window, **kwargs):
        self.window = window
        self.webview = None
        self.enable_dismiss = False
        super(BrowserView, self).__init__(**kwargs)
        Clock.schedule_once(lambda dt: run_ui_thread(self.create_webview), 0)

    def create_webview(self, *args):
        def js_api_handler(func, params, id):
            print(func, params, id)
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

        self.webview = WebViewA(activity)
        settings = self.webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setUseWideViewPort(False)
        settings.setLoadWithOverviewMode(True)
        settings.setSupportZoom(self.window.zoomable)
        settings.setBuiltInZoomControls(False)

        webview_callback_wrapper = EventCallbackWrapper(webview_callback)
        webview_client = PyWebViewClient()
        webview_client.setCallback(webview_callback_wrapper, True) # TODO SSL
        self.webview.setWebViewClient(webview_client)

        chrome_callback_wrapper = EventCallbackWrapper(chrome_callback)
        chrome_client = PyWebChromeClient()
        chrome_client.setCallback(chrome_callback_wrapper)
        self.webview.setWebChromeClient(chrome_client)

        activity.setContentView(self.webview)

        js_api_callback_wrapper = JsApiCallbackWrapper(js_api_handler)
        js_interface = PyJavaScriptInterface()
        js_interface.setCallback(js_api_callback_wrapper)
        self.webview.addJavascriptInterface(js_interface, 'external')

        if True or settings['ALLOW_DOWNLOADS']:
            self.webview.setDownloadListener(DownloadListener())

        if self.window.real_url:
            self.webview.loadUrl(self.window.real_url)
        elif self.window.html:
            self.webview.loadDataWithBaseURL(None, self.window.html, 'text/html', 'UTF-8', None)

        self.window.events.shown.set()

    def on_dismiss(self):
        def _dismiss():
            self.enable_dismiss = False
            self.webview.clearHistory()
            self.webview.clearCache(True)
            self.webview.clearFormData()
            self.webview.destroy()
            self.layout = None
            self.webview = None

        if self.enable_dismiss:
            run_ui_thread(_dismiss)

    # @run_on_ui_thread
    # def on_size(self, instance, size):
    #     if self.webview:
    #         params = self.webview.getLayoutParams()
    #         params.width = size[0]
    #         params.height = size[1]
    #         self.webview.setLayoutParams(params)

    def pause(self):
        def _pause():
            self.webview.pauseTimers()
            self.webview.onPause()

        if self.webview:
            run_on_ui_thread(_pause)

    def resume(self):
        def _resume():
            self.webview.onResume()
            self.webview.resumeTimers()

        if self.webview:
            run_on_ui_thread(_resume)



    def _back_pressed(self):
        def _back():
            if self.webview.canGoBack():
                self.webview.goBack()
            else:
                self.dismiss()

        if self.webview:
            run_on_ui_thread(_back)

        return True

class AndroidApp(App):
    def __init__(self, window):
        self.window = window
        super().__init__()

    def build(self):
        self.view = BrowserView(self.window)
        return self.view


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, _):
    pass


def create_window(window):
    global app
    app = AndroidApp(window)
    app.run()


def setup_app():
    pass


@run_on_ui_thread
def load_url(url, _):
    app.window.events.loaded.clear()
    app.view.webview.loadUrl(url)


@run_on_ui_thread
def load_html(html_content, base_uri, _):
    app.window.events.loaded.clear()
    app.view.webview.loadDataWithBaseURL(base_uri, html_content, "text/html", "UTF-8", None)


def evaluate_js(js_code, unique_id):
    def callback(event, result):
        nonlocal js_result
        js_result = json.loads(json.loads(result)) if result else None
        lock.release()

    def _evaluate_js(arg1, arg2):
        callback_wrapper = EventCallbackWrapper(callback)
        value_callback = JavascriptValueCallback()
        value_callback.setCallback(callback_wrapper)
        app.view.webview.evaluateJavascript(js_code, value_callback)

    try:
        lock = Semaphore(0)
        js_result = None

        run_ui_thread(_evaluate_js)
        lock.acquire()
        return js_result
    except Exception as e:
        print(e)


def get_cookies(_):
    def _cookies(arg1, arg2):
        nonlocal cookies
        cookie_manager = CookieManager.getInstance()
        current_url = app.view.webview.getUrl()

        raw_cookies = cookie_manager.getCookie(current_url)

        if raw_cookies:
            print(raw_cookies)
            cookies = raw_cookies.split(';')

        lock.release()

    cookies = []
    lock = Semaphore(0)
    run_ui_thread(_cookies)
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
    pass


def hide(_):
    pass


def minimize(_):
    pass


def move(_):
    pass


def restore(_):
    pass


def resize(width, height, _, fix_point):
    pass


def destroy_window():
    App.get_running_app().stop()


def set_title(title, _):
    pass


def set_on_top(_, on_top):
    pass


def toggle_fullscreen(_):
    pass


def add_tls_cert(certfile):
    pass