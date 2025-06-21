import logging
import json
from threading import Semaphore
from urllib.parse import urlparse

from jnius import cast, autoclass
from android.runnable import run_on_ui_thread  # noqa
from android.activity import _activity as activity# noqa

from webview import _state, settings
from webview.models import Request, Response
from webview.platforms.android.app import App
from webview.platforms.android.jclass import (
    CookieManager,
    WebView,
    PyWebViewClient,
    PyWebChromeClient,
    PyJavascriptInterface,
    AlertDialogBuilder,
    DownloadManagerRequest,
    Uri,
    Environment,
    View,
    KeyEvent,
    Context
)
from webview.platforms.android.jinterface import (
    EventCallbackWrapper,
    RequestInterceptor,
    JsApiCallbackWrapper,
    KeyListener,
    ValueCallback,
    DownloadListener
)
from webview.util import create_cookie, js_bridge_call, inject_pywebview


logger = logging.getLogger('pywebview')

renderer = 'android-webkit'
app = None


class BrowserView:
    def __init__(self, window):
        self.pywebview_window = window
        self.webview = None
        self.dialog = None
        self.pywebview_window.native = self
        self.is_fullscreen = False
        self.create_webview()

    @run_on_ui_thread
    def create_webview(self):
        def js_api_handler(func, params, id):
            js_bridge_call(self.pywebview_window, func, json.loads(params), id)

        def chrome_callback(event, data):
            print(event, data)

        def webview_callback(event, data):
            if event == 'onPageFinished':
                inject_pywebview(renderer, self.pywebview_window)
                cookiemanager = CookieManager.getInstance()
                if not _state['private_mode']:
                    cookiemanager.setAcceptCookie(True)
                    cookiemanager.acceptCookie()
                    cookiemanager.flush()
                else:
                    cookiemanager.setAcceptCookie(False)

            elif event == 'onCookiesReceived':
                cookies = json.loads(data)
                url = cookies['url']

                if url in self._cookies:
                    self._cookies[url] = list(set(self._cookies[url] + cookies['cookies']))
                else:
                    self._cookies[url] = cookies['cookies']
            elif event == 'onReceivedHttpError':
                response_data = json.loads(data)
                response = Response(
                    response_data.get('url', ''),
                    response_data.get('statusCode', 0),
                    response_data.get('headers', {})
                )
                self.pywebview_window.events.response_received.set(response)

        self._cookies = {}
        self.webview = WebView(activity)
        webview_settings = self.webview.getSettings()
        webview_settings.setAllowFileAccessFromFileURLs(True)
        webview_settings.setJavaScriptEnabled(True)
        webview_settings.setUseWideViewPort(False)
        webview_settings.setLoadWithOverviewMode(True)
        webview_settings.setSupportZoom(self.pywebview_window.zoomable)
        webview_settings.setBuiltInZoomControls(False)
        webview_settings.setDomStorageEnabled(not _state['private_mode'])

        if _state['user_agent']:
            webview_settings.setUserAgentString(_state['user_agent'])

        self._webview_callback_wrapper = EventCallbackWrapper(webview_callback)
        self._webview_client = webview_client = PyWebViewClient()
        webview_client.setCallback(self._webview_callback_wrapper, _state['ssl'] or settings['IGNORE_SSL_ERRORS'])
        self._request_interceptor = RequestInterceptor(self._on_request, self._on_response)
        webview_client.setRequestInterceptor(self._request_interceptor)

        self.webview.setWebViewClient(webview_client)

        self._chrome_callback_wrapper = EventCallbackWrapper(chrome_callback)
        self._chrome_client = chrome_client = PyWebChromeClient()
        chrome_client.setCallback(self._chrome_callback_wrapper)
        self.webview.setWebChromeClient(chrome_client)

        self._js_api_callback_wrapper = JsApiCallbackWrapper(js_api_handler)
        self._js_interface = js_interface = PyJavascriptInterface()
        js_interface.setCallback(self._js_api_callback_wrapper)
        self.webview.addJavascriptInterface(js_interface, 'external')

        if settings['ALLOW_DOWNLOADS']:
            def _on_download_start(url, *_):
                context = activity.getApplicationContext()
                visibility = DownloadManagerRequest.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
                dir_type = Environment.DIRECTORY_DOWNLOADS
                uri = Uri.parse(url)
                filepath = uri.getLastPathSegment()
                request = DownloadManagerRequest(uri)
                request.setNotificationVisibility(visibility)
                request.setDestinationInExternalFilesDir(context, dir_type, filepath)
                dm = cast("android.app.DownloadManager", activity.getSystemService(Context.DOWNLOAD_SERVICE))
                dm.enqueue(request)

            self._download_listener = DownloadListener(_on_download_start)
            self.webview.setDownloadListener(self._download_listener)

        self._key_listener = KeyListener(self._back_pressed)
        self.webview.setOnKeyListener(self._key_listener)
        self.pywebview_window.events.before_show.set()

        if self.pywebview_window.real_url:
            self.webview.loadUrl(self.pywebview_window.real_url)
        elif self.pywebview_window.html:
            self.webview.loadDataWithBaseURL(None, self.pywebview_window.html, 'text/html', 'UTF-8', None)

        if self.pywebview_window.fullscreen:
            toggle_fullscreen(self.pywebview_window)

        self.pywebview_window.events.shown.set()
        activity.setContentView(self.webview)

    def _on_request(self, url: str, method: str, headers_json: str):
        headers = json.loads(headers_json) if headers_json else {}
        original_headers = headers.copy()

        request = Request(url, method, headers)
        self.pywebview_window.events.request_sent.set(request)

        if request.headers != original_headers:
            logger.debug('Request headers mutated. Original: %s, Mutated: %s', original_headers, request.headers)

            return json.dumps(request.headers)

        return None

    def _on_response(self, url: str, status_code: int, headers_json: str):
        headers = json.loads(headers_json) if headers_json else {}

        response = Response(url, status_code, headers)
        self.pywebview_window.events.response_received.set(response)

    def dismiss(self):
        if _state['private_mode']:
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
            self.pywebview_window.closed.set()
            self.dialog = None
            app.stop()

        if self.dialog:
            return

        String = autoclass("java.lang.String")
        message = String(self.pywebview_window.localization['global.quitConfirmation'])
        quit_msg = String(self.pywebview_window.localization['global.quit'])
        cancel_msg = String(self.pywebview_window.localization['global.cancel'])

        self.dialog = AlertDialogBuilder(activity) \
            .setMessage(message) \
            .setPositiveButton(quit_msg, quit) \
            .setNegativeButton(cancel_msg, cancel) \
            .setOnCancelListener(cancel) \
            .show()

    def _back_pressed(self, v, key_code, event):
        if not (event.getAction() == KeyEvent.ACTION_DOWN and key_code == KeyEvent.KEYCODE_BACK):
            return False
        elif self.webview.canGoBack():
            self.webview.goBack()
        elif self.pywebview_window.events.closing.set():
            pass
        elif self.pywebview_window.confirm_close:
            self._quit_confirmation()
        else:
            app.pause()
            self.pywebview_window.closed.set()
        return True

    def get_size(self):
        return self.webview.getWidth(), self.webview.getHeight()

    def get_url(self):
        return self.webview.getUrl()

    @run_on_ui_thread
    def load_url(self, url):
        self.webview.loadUrl(url)

    @run_on_ui_thread
    def load_data_with_base_url(self, base_uri, html_content):
        self.webview.loadDataWithBaseURL(base_uri, html_content, 'text/html', 'UTF-8', None)


class AndroidApp(App):
    def __init__(self, window):
        self.window = window
        self.first_show = True
        super().__init__()

    def build_view(self):
        self.view = BrowserView(self.window)
        return self.view

    def on_pause(self, _):
        self.view.webview.pauseTimers()
        self.view.webview.onPause()

        logger.debug('pausing initiated')

    def on_resume(self, _):
        logger.debug('resuming')
        self.view.webview.onResume()
        self.view.webview.resumeTimers()


def create_file_dialog(*_):
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


def load_url(url, _):
    app.view._cookies = {}
    app.view.load_url(url)


def load_html(html_content, base_uri, _):
    app.view._cookies = {}
    app.view.load_data_with_base_url(base_uri, html_content)


def evaluate_js(js_code, _, parse_json=True):
    def callback(result):
        nonlocal js_result
        js_result = json.loads(result) if parse_json and result else result
        lock.release()

    @run_on_ui_thread
    def _evaluate_js():
        value_callback = ValueCallback(callback)
        app.view.webview.evaluateJavascript(js_code, value_callback)

    lock = Semaphore(0)
    js_result = None

    _evaluate_js()
    lock.acquire()
    return js_result


def clear_cookies(_):
    CookieManager.getInstance().removeAllCookies(None)


def get_cookies(_):
    cookies = []
    raw_cookies = app.view._cookies
    full_url = app.view.get_url()
    url = urlparse(full_url)
    url = f'{url.scheme}://{url.netloc}'

    if url in raw_cookies:
        cookies = [create_cookie(c) for c in raw_cookies[url]]

    for c in {x for v in raw_cookies.values() for x in v}:
        cookie = create_cookie(c)
        domain = next(iter(cookie.values())).get('domain')

        if not domain:
            continue

        if domain.startswith('.') and url.endswith(domain.lstrip('.')) or not domain.startswith('.') and url == domain:
            cookies.append(cookie)

    return cookies


def get_current_url(_):
    return app.view.get_url()


def get_screens():
    logger.warning('Screen information is not supported on Android')
    return []


def get_size(_):
    return app.view.get_size()


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


@run_on_ui_thread
def toggle_fullscreen(_):
    is_fullscreen = app.view.is_fullscreen

    try:
        if not is_fullscreen:
            option = (View.SYSTEM_UI_FLAG_FULLSCREEN |
                      View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                      View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
                      View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
                      View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
                      View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN)
            app.view.webview.setSystemUiVisibility(option)
            app.view.is_fullscreen = True
        else:
            option = View.SYSTEM_UI_FLAG_VISIBLE
            app.view.webview.setSystemUiVisibility(option)
            app.view.is_fullscreen = False
    except Exception as e:
        logger.error(f"Error toggling fullscreen: {e}")


def add_tls_cert(certfile):
    pass
