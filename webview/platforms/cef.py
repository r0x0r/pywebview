import json
import logging
import os
import shutil
import sys
import webbrowser
from copy import copy
from ctypes import windll
from functools import wraps
from threading import Event
from time import sleep

from cefpython3 import cefpython as cef

from webview import _settings, settings
from webview.js import dom_json
from webview.js.css import disable_text_select
from webview.util import DEFAULT_HTML, create_cookie, js_bridge_call, inject_pywebview

sys.excepthook = cef.ExceptHook
instances = {}

logger = logging.getLogger(__name__)

browser_settings = {}
command_line_switches = {}


def _set_dpi_mode(enabled):
    """ """
    import winreg  # Python 3

    try:
        dpi_support = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers',
            0,
            winreg.KEY_ALL_ACCESS,
        )
    except WindowsError:
        dpi_support = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers',
            0,
            winreg.KEY_ALL_ACCESS,
        )

    try:
        subprocess_path = os.path.join(sys._MEIPASS, 'subprocess.exe')
    except:
        subprocess_path = os.path.join(os.path.dirname(cef.__file__), 'subprocess.exe')

    if enabled:
        winreg.SetValueEx(dpi_support, subprocess_path, 0, winreg.REG_SZ, '~HIGHDPIAWARE')
    else:
        winreg.DeleteValue(dpi_support, subprocess_path)

    winreg.CloseKey(dpi_support)


class JSBridge:
    def __init__(self, window, eval_events):
        self.results = {}
        self.window = window
        self.eval_events = eval_events

    def return_result(self, result, uid):
        self.results[uid] = json.loads(result) if result else None
        self.eval_events[uid].set()

    def call(self, func_name, param, value_id):
        js_bridge_call(self.window, func_name, json.loads(param), value_id)


renderer = 'cef'


class CookieVisitor:
    def Visit(self, cookie, count, total, delete_cookie_out):
        data = {
            'name': cookie.GetName(),
            'value': cookie.GetValue(),
            'path': cookie.GetPath(),
            'domain': cookie.GetDomain(),
            'expires': cookie.GetExpires().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'secure': cookie.GetSecure(),
            'httponly': cookie.GetHttpOnly(),
        }

        cookie = create_cookie(data)
        self.cookies.append(cookie)

        if count + 1 == total:
            self.lock.set()

        return True


class Browser:
    def __init__(self, window, handle, browser, parent):
        self.window = window
        self.handle = handle
        self.browser = browser
        self.parent = parent
        self.text_select = window.text_select
        self.uid = window.uid
        self.loaded = window.events.loaded
        self.shown = window.events.shown
        self.inner_hwnd = self.browser.GetWindowHandle()
        self.eval_events = {}
        self.js_bridge = JSBridge(window, self.eval_events)
        self.initialized = False

    def initialize(self):
        if self.initialized:
            return

        self.cookie_manager = cef.CookieManager.GetGlobalManager()
        self.cookie_visitor = CookieVisitor()

        self.browser.GetJavascriptBindings().Rebind()
        self.browser.ExecuteJavascript(inject_pywebview(self.window, 'cef'))

        if not self.text_select:
            self.browser.ExecuteJavascript(disable_text_select)

        self.browser.ExecuteJavascript(dom_json.src)

        sleep(0.1)  # wait for window.pywebview to load
        self.initialized = True
        self.loaded.set()

    def close(self):
        self.browser.CloseBrowser(True)

    def resize(self, width, height):
        screen = self.parent.RectangleToScreen(self.parent.ClientRectangle)
        height_diff = screen.Top - self.parent.Top + 12
        width_diff = self.parent.Right - screen.Right + 12

        windll.user32.SetWindowPos(
            self.inner_hwnd,
            0,
            0,
            0,
            width - width_diff,
            height - height_diff,
            0x0002 | 0x0004 | 0x0010,
        )
        self.browser.NotifyMoveOrResizeStarted()

    def evaluate_js(self, code, unique_id):
        self.loaded.wait()

        self.eval_events[unique_id] = Event()
        eval_script = """
            try {{
                {0}
            }} catch(e) {{
                console.error(e.stack);
                window.external.return_result(null, '{1}');
            }}
        """.format(
            code, unique_id
        )

        result = self.browser.ExecuteJavascript(eval_script)
        self.eval_events[unique_id].wait()  # result is obtained via JSBridge.return_result

        result = copy(self.js_bridge.results[unique_id])

        del self.eval_events[unique_id]
        del self.js_bridge.results[unique_id]

        return result

    def get_cookies(self):
        self.loaded.wait()
        self.cookie_visitor.cookies = []
        self.cookie_visitor.lock = Event()
        self.cookie_manager.VisitUrlCookies(self.browser.GetUrl(), True, self.cookie_visitor)
        self.cookie_visitor.lock.wait()

        return self.cookie_visitor.cookies

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

    def focus(self):
        self.browser.SendFocusEvent(True)


def find_instance(browser):
    for instance in instances.values():
        if instance.browser is browser:
            return instance

    return None


class LoadHandler:
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
            logger.error('CEF window with uid {0} does not exist'.format(uid))
            return

        return func(*args, **kwargs)

    return wrapper


def init(_, cache_dir):
    global _initialized

    if not _initialized:
        if sys.platform == 'win32':
            _set_dpi_mode(True)

        default_settings = {
            'multi_threaded_message_loop': True,
            'context_menu': {'enabled': _settings['debug']},
        }

        default_command_line_switches = {
            'enable-media-stream': '',
        }

        if not _settings['debug']:
            default_settings['remote_debugging_port'] = -1

        if _settings['user_agent']:
            default_settings['user_agent'] = _settings['user_agent']

        if cache_dir:
            default_settings['cache_path'] = cache_dir

        if settings['ALLOW_FILE_URLS']:
            default_command_line_switches['allow-file-access-from-files'] = ''

        resource_root = getattr(sys, '_MEIPASS', os.path.dirname(cef.__file__))

        default_settings.update(
            {
                'resources_dir_path': resource_root,
                'locales_dir_path': os.path.join(resource_root, 'locales'),
                'browser_subprocess_path': os.path.join(resource_root, 'subprocess.exe'),
            }
        )

        all_settings = dict(default_settings, **browser_settings)
        all_command_line_switches = dict(default_command_line_switches, **command_line_switches)
        cef.Initialize(settings=all_settings, commandLineSwitches=all_command_line_switches)
        cef.DpiAware.EnableHighDpiSupport()

        _initialized = True


def create_browser(window, handle, alert_func, parent):
    def _create():
        real_url = (
            'data:text/html,{0}'.format(window.html)
            if window.html
            else window.real_url or 'data:text/html,{0}'.format(DEFAULT_HTML)
        )

        default_browser_settings = {}
        all_browser_settings = dict(default_browser_settings, **browser_settings)

        cef_browser = cef.CreateBrowserSync(
            window_info=window_info, settings=all_browser_settings, url=real_url
        )
        browser = Browser(window, handle, cef_browser, parent)

        bindings = cef.JavascriptBindings()
        bindings.SetObject('external', browser.js_bridge)
        bindings.SetFunction('alert', alert_func)

        cef_browser.SetJavascriptBindings(bindings)
        cef_browser.SetClientHandler(LoadHandler())
        instances[window.uid] = browser
        cef_browser.SendFocusEvent(True)
        window.events.shown.set()
        cef_browser.SendFocusEvent(True)

        if _settings['debug'] and settings['OPEN_DEVTOOLS_IN_DEBUG']:
            cef_browser.ShowDevTools()

    window_info = cef.WindowInfo()
    window_info.SetAsChild(handle)
    cef.PostTask(cef.TID_UI, _create)


@_cef_call
def focus(uid):
    instance = instances[uid]
    instance.focus()


@_cef_call
def load_html(html, uid):
    instance = instances[uid]
    instance.load_html(html)


@_cef_call
def load_url(url, uid):
    instance = instances[uid]
    instance.load_url(url)


@_cef_call
def evaluate_js(code, result, uid):
    instance = instances[uid]
    return instance.evaluate_js(code, result)


@_cef_call
def get_cookies(uid):
    instance = instances[uid]
    return instance.get_cookies()


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
    instance = instances[uid]
    instance.resize(width, height)


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

        if os.path.exists('error.log') and not _settings['debug']:
            os.remove('error.log')

        if sys.platform == 'win32':
            _set_dpi_mode(False)

    except Exception as e:
        logger.debug(e, exc_info=True)

    cef.Shutdown()


_initialized = False
