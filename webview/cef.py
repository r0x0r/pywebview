import json
import sys
import atexit

from functools import wraps
from uuid import uuid1
from threading import Event
from cefpython3 import cefpython as cef
from copy import copy

from .js import cef as cef_script, api
from .js.css import disable_text_select
from webview import _webview_ready, _js_bridge_call
from webview.util import escape_string, inject_base_uri, parse_api_js, blank_html


sys.excepthook = cef.ExceptHook
instances = {}


class JSBridge:
    def __init__(self, eval_events, api, uid):
        self.results = {}
        self.eval_events = eval_events
        self.api = api
        self.uid = uid
        
    def return_result(self, result, uid):
        self.results[uid] = json.loads(result)
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

        bindings = cef.JavascriptBindings()

        if self.api:
            self.browser.ExecuteJavascript(parse_api_js(self.api))
        else:
            self.browser.ExecuteJavascript('window.pywebview={ _evalResults: {} }')

        bindings.SetObject('external', self.js_bridge)
        self.browser.SetJavascriptBindings(bindings)
        self.browser.ExecuteJavascript(cef_script.src)
        self.initialized = True
        self.loaded.set()

    def close(self):
        self.browser.CloseBrowser()

    def evaluate_js(self, code):
        self.loaded.wait()

        id_ = uuid1().hex[:8]
        self.eval_events[id_] = Event()
        self.browser.ExecuteJavascript('window.pywebview._evalResults["{0}"] = {1}'.format(id_, code))
        self.browser.ExecuteJavascript('window.pywebview._checkEvalResult("{0}")'.format(id_))
        self.eval_events[id_].wait()
        result = copy(self.js_bridge.results[id_])

        del self.eval_events[id_]
        del self.js_bridge.results[id_]

        return result

    def get_current_url(self):
        self.loaded.wait()
        return self.browser.GetUrl()

    def load_url(self, url):
        self.browser.LoadUrl(url)

    def load_html(self, html):
        self.browser.LoadUrl('data:text/html,{0}'.format(html))


def find_instance(browser):
    for instance in instances.values():
        if instance.browser is browser:
            return instance

    return None


class LoadHandler(object):
    def OnLoadingStateChange(self, browser, is_loading, **_):
        if not is_loading:
            instance = find_instance(browser)
            assert(instance is not None)
            instance.initialize()


def _cef_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        uid = args[-1]

        if uid not in instances:
            raise Exception('CEF window with uid {0} does not exist'.format(uid))

        _webview_ready.wait()
        return func(*args, **kwargs)

    return wrapper

def init():
    global _initialized

    if not _initialized:
        settings = {'multi_threaded_message_loop': True}
        cef.Initialize(settings=settings)
        cef.DpiAware.EnableHighDpiSupport()
        _initialized = True


def create_browser(uid, handle, url=None, js_api=None, text_select=False):
    def _create():
        real_url = url or 'data:text/html,{0}'.format(blank_html)
        browser = cef.CreateBrowserSync(window_info=window_info, url=real_url)
        instances[uid] = Browser(handle, browser, js_api, text_select, uid)
        browser.SetClientHandler(LoadHandler())

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
    return instance.get_current_url()


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
    cef.Shutdown()

atexit.register(shutdown)

_initialized = False
init()
