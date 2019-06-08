import json
import logging
import os
import shutil
import sys
import webbrowser

from functools import wraps
from uuid import uuid1
from threading import Event
from cefpython3 import cefpython as cef
from copy import copy

from .js.css import disable_text_select
from webview import _js_bridge_call
from webview.util import parse_api_js, default_html


sys.excepthook = cef.ExceptHook
instances = {}

logger = logging.getLogger(__name__)


class JSBridge:
    def __init__(self, eval_events, api, uid):
        self.results = {}
        self.eval_events = eval_events
        self.api = api
        self.uid = uid

    def return_result(self, result, uid):
        self.results[uid] = json.loads(result) if result else None
        self.eval_events[uid].set()

    def call(self, func_name, param):
        _js_bridge_call(self.uid, self.api, func_name, param)


class Browser:
    def __init__(self, handle, browser, api, text_select, uid):
        self.handle = handle
        self.browser = browser
        self.api = api
        self.text_select = text_select
        self.uid = uid

        self.eval_events = {}
        self.js_bridge = JSBridge(self.eval_events, api, uid)
        self.initialized = False
        self.loaded = Event()

    def initialize(self):
        if self.initialized:
            return

        self.browser.GetJavascriptBindings().Rebind()

        if self.api:
            self.browser.ExecuteJavascript(parse_api_js(self.api))

        if not self.text_select:
            self.browser.ExecuteJavascript(disable_text_select)

        self.initialized = True
        self.loaded.set()

    def close(self):
        self.browser.CloseBrowser(True)

    def evaluate_js(self, code):
        self.loaded.wait()
        eval_script = """
            try {{
                window.external.return_result({0}, '{1}');
            }} catch(e) {{
                console.error(e.stack);
                window.external.return_result(null, '{1}');
            }}
        """

        id_ = uuid1().hex[:8]
        self.eval_events[id_] = Event()
        self.browser.ExecuteJavascript(eval_script.format(code, id_))
        self.eval_events[id_].wait()  # result is obtained via JSBridge.return_result

        result = copy(self.js_bridge.results[id_])

        del self.eval_events[id_]
        del self.js_bridge.results[id_]

        return result

    def get_current_url(self):
        self.loaded.wait()
        return self.browser.GetUrl()

    def load_url(self, url):
        self.initialized = False
        self.loaded.clear()
        self.browser.LoadUrl(url)

    def load_html(self, html):
        self.initialized = False
        self.loaded.clear()
        self.browser.LoadUrl('data:text/html,{0}'.format(html))


def find_instance(browser):
    for instance in instances.values():
        if instance.browser is browser:
            return instance

    return None


class LoadHandler(object):
    def OnBeforePopup(self, **args):
        url = args['target_url']
        user_gesture = args['user_gesture']

        if user_gesture:
            webbrowser.open(url)

        return True

    def OnLoadingStateChange(self, browser, is_loading, **_):
        instance = find_instance(browser)

        if instance is not None:
            if is_loading:
                instance.initialized = False
            else:
                instance.initialize()
        else:
            logger.debug('CEF instance is not found %s ' % browser)


def _cef_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        uid = args[-1]

        if uid not in instances:
            raise Exception('CEF window with uid {0} does not exist'.format(uid))

        _webview_ready.wait()
        return func(*args, **kwargs)

    return wrapper


_webview_ready = None


def init(webview_ready, debug):
    global _initialized, _webview_ready
    _webview_ready = webview_ready

    if not _initialized:
        settings = {
            'multi_threaded_message_loop': True,
            'context_menu': {
                'enabled': debug
            }
        }

        try: # set paths under Pyinstaller's one file mode
            settings.update({
                'resources_dir_path': sys._MEIPASS,
                'locales_dir_path': os.path.join(sys._MEIPASS, 'locales'),
                'browser_subprocess_path': os.path.join(sys._MEIPASS, 'subprocess.exe'),
            })
        except Exception:
            pass

        cef.Initialize(settings=settings)
        cef.DpiAware.EnableHighDpiSupport()
        _initialized = True


def create_browser(uid, handle, alert_func, url=None, js_api=None, text_select=False):
    def _create():
        real_url = url or 'data:text/html,{0}'.format(default_html)
        cef_browser = cef.CreateBrowserSync(window_info=window_info, url=real_url)
        browser = Browser(handle, cef_browser, js_api, text_select, uid)

        bindings = cef.JavascriptBindings()
        bindings.SetObject('external', browser.js_bridge)
        bindings.SetFunction('alert', alert_func)

        cef_browser.SetJavascriptBindings(bindings)
        cef_browser.SetClientHandler(LoadHandler())

        instances[uid] = browser
        _webview_ready.set()

    window_info = cef.WindowInfo()
    window_info.SetAsChild(handle)
    cef.PostTask(cef.TID_UI, _create)


@_cef_call
def load_html(html, uid):
    instance = instances[uid]
    instance.load_html(html)


@_cef_call
def load_url(url, uid):
    instance = instances[uid]
    instance.load_url(url)


@_cef_call
def evaluate_js(code, uid):
    instance = instances[uid]
    return instance.evaluate_js(code)


@_cef_call
def get_current_url(uid):
    instance = instances[uid]
    url = instance.get_current_url()

    if url.startswith('data:text/html,'):
        return None
    else:
        return url


@_cef_call
def resize(width, height, uid):
    hwnd = instances[uid].handle
    lparam = width << 16 & height
    cef.WindowUtils.OnSize(hwnd, 5, 0, lparam)


@_cef_call
def close_window(uid):
    instance = instances[uid]
    instance.close()
    del instances[uid]


def shutdown():
    try:
        if os.path.exists('blob_storage'):
            shutil.rmtree('blob_storage')

        if os.path.exists('webrtc_event_logs'):
            shutil.rmtree('webrtc_event_logs')

        if os.path.exists('error.log'):
            os.remove('error.log')

    except Exception as e:
        logger.debug(e, exc_info=True)

    cef.Shutdown()


_initialized = False
