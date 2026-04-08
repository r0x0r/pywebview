import json
import logging
import os
from threading import Semaphore

try:
    import clr
except Exception:
    os.environ['PYTHONNET_RUNTIME'] = 'coreclr'
    import clr

from webview import Window, _state
from webview import settings as webview_settings
from webview.platforms.webview2core import WebView2Core
from webview.util import (
    create_cookie,
    get_app_root,
    inject_pywebview,
    interop_dll_path,
)

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms  # noqa: E402
from System import Action, Func, Object, String, Type, Uri  # noqa: E402
from System.Collections.Generic import List  # noqa: E402
from System.Drawing import Color  # noqa: E402
from System.Globalization import CultureInfo  # noqa: E402
from System.Threading.Tasks import Task, TaskScheduler  # noqa: E402

clr.AddReference(interop_dll_path('Microsoft.Web.WebView2.Core.dll'))
clr.AddReference(interop_dll_path('Microsoft.Web.WebView2.WinForms.dll'))

from Microsoft.Web.WebView2.Core import (  # noqa: E402
    CoreWebView2Cookie,
    CoreWebView2ServerCertificateErrorAction,
    CoreWebView2WebResourceContext,
)
from Microsoft.Web.WebView2.WinForms import CoreWebView2CreationProperties, WebView2  # noqa: E402

for platform in ('win-arm64', 'win-x64', 'win-x86'):
    os.environ['Path'] += ';' + interop_dll_path(platform)


logger = logging.getLogger('pywebview')
renderer = 'edgechromium'


class WinFormsEdgeChrome(WebView2Core):
    def __init__(self, form: WinForms.Form, window: Window, cache_dir: str):
        super().__init__(window)

        self.webview = WebView2()
        props = CoreWebView2CreationProperties()

        runtime_path = webview_settings['WEBVIEW2_RUNTIME_PATH']
        if runtime_path:
            if not os.path.isabs(runtime_path):
                runtime_path = os.path.join(get_app_root(), runtime_path)
            if os.path.exists(runtime_path):
                props.BrowserExecutableFolder = runtime_path
                logger.debug(f'Using custom WebView2 runtime: {runtime_path}')
            else:
                logger.warning(
                    f'Custom WebView2 runtime path does not exist: {runtime_path}. Using system WebView2.'
                )

        props.UserDataFolder = cache_dir
        self.user_data_folder = props.UserDataFolder
        props.set_IsInPrivateModeEnabled(_state['private_mode'])
        props.AdditionalBrowserArguments = self._build_browser_args()

        self.webview.CreationProperties = props

        self.form = form
        form.Controls.Add(self.webview)

        self.js_results = {}
        self.webview.Dock = WinForms.DockStyle.Fill
        self.webview.BringToFront()
        self.webview.CoreWebView2InitializationCompleted += self.on_webview_ready
        self.webview.NavigationStarting += self.on_navigation_start
        self.webview.NavigationCompleted += self.on_navigation_completed
        self.webview.WebMessageReceived += self.on_script_notify
        self.syncContextTaskScheduler = TaskScheduler.FromCurrentSynchronizationContext()

        r, g, b = self._parse_hex_color(window.background_color)
        self.webview.DefaultBackgroundColor = Color.FromArgb(255, r, g, b)

        if window.transparent:
            self.webview.DefaultBackgroundColor = Color.Transparent

        self.webview.EnsureCoreWebView2Async(None)

    def _get_browser_process_id(self) -> int:
        return int(self.webview.CoreWebView2.BrowserProcessId)

    def _release_webview(self):
        self.webview.Dispose()

    def evaluate_js(self, script: str, parse_json: bool):
        def _callback(res):
            nonlocal result
            if parse_json and res is not None:
                try:
                    result = json.loads(res)
                except Exception:
                    result = res
            else:
                result = res
            semaphore.release()

        result = None
        semaphore = Semaphore(0)

        try:
            self.webview.Invoke(
                Func[Object](
                    lambda: self.webview.ExecuteScriptAsync(script).ContinueWith(
                        Action[Task[String]](lambda task: _callback(json.loads(task.Result))),
                        self.syncContextTaskScheduler,
                    )
                )
            )
            semaphore.acquire()
        except Exception:
            logger.exception('Error occurred in script')
            semaphore.release()

        return result

    def clear_cookies(self):
        self.webview.CoreWebView2.CookieManager.DeleteAllCookies()

    def get_cookies(self, cookies, semaphore):
        def _callback(task):
            for c in task.Result:
                _cookies.append(c)
            self.webview.Invoke(Func[Type](_parse_cookies))

        def _parse_cookies():
            # cookies must be accessed in the main thread, otherwise an exception is thrown
            # https://github.com/MicrosoftEdge/WebView2Feedback/issues/1976
            for c in _cookies:
                same_site = None if c.SameSite == 0 else str(c.SameSite).lower()
                try:
                    data = {
                        'name': c.Name,
                        'value': c.Value,
                        'path': c.Path,
                        'domain': c.Domain,
                        'expires': c.Expires.ToString('r', CultureInfo.GetCultureInfo('en-US')),
                        'secure': c.IsSecure,
                        'httponly': c.IsHttpOnly,
                        'samesite': same_site,
                    }
                    cookie = create_cookie(data)
                    cookies.append(cookie)
                except Exception as e:
                    logger.exception(e)
            semaphore.release()

        _cookies = []
        self.webview.CoreWebView2.CookieManager.GetCookiesAsync(self.url).ContinueWith(
            Action[Task[List[CoreWebView2Cookie]]](_callback), self.syncContextTaskScheduler
        )

    def load_html(self, content, _):
        self.html = content
        self.ishtml = True

        if self.webview.CoreWebView2:
            self.webview.CoreWebView2.NavigateToString(self.html)
        else:
            self.webview.EnsureCoreWebView2Async(None)

    def load_url(self, url: str):
        self.ishtml = False
        self.webview.Source = Uri(url)

    def _show_alert(self, message: str):
        WinForms.MessageBox.Show(message)

    def _extract_dropped_files(self, additional_objects) -> list:
        return [
            (os.path.basename(file.Path), file.Path)
            for file in list(additional_objects)
            if 'CoreWebView2File' in str(type(file))
        ]

    def _apply_settings(self, settings):
        settings.AreBrowserAcceleratorKeysEnabled = _state['debug']
        settings.AreDefaultContextMenusEnabled = _state['debug']
        settings.AreDefaultScriptDialogsEnabled = True
        settings.AreDevToolsEnabled = _state['debug']
        settings.IsBuiltInErrorPageEnabled = True
        settings.IsScriptEnabled = True
        settings.IsWebMessageEnabled = True
        settings.IsStatusBarEnabled = _state['debug']
        settings.IsSwipeNavigationEnabled = False
        settings.IsZoomControlEnabled = True
        if _state['user_agent']:
            settings.UserAgent = _state['user_agent']

    def on_certificate_error(self, _, args):
        args.set_Action(CoreWebView2ServerCertificateErrorAction.AlwaysAllow)

    def on_script_notify(self, _, args):
        try:
            self._route_script_message(args.get_WebMessageAsJson(), args.get_AdditionalObjects())
        except Exception:
            logger.exception('Exception occurred during on_script_notify')

    def on_new_window_request(self, sender, args):
        args.set_Handled(True)
        self._handle_new_window_request(str(args.get_Uri()))

    def on_source_changed(self, sender, args):
        self.url = sender.Source
        self.ishtml = False

    def on_webview_ready(self, sender, args):
        if not args.IsSuccess:
            logger.error(
                'WebView2 initialization failed with exception:\n '
                + str(args.InitializationException)
            )
            return

        self.webview.CoreWebView2.SourceChanged += self.on_source_changed
        sender.CoreWebView2.NewWindowRequested += self.on_new_window_request
        sender.CoreWebView2.AddWebResourceRequestedFilter('*', CoreWebView2WebResourceContext.All)
        sender.CoreWebView2.WebResourceResponseReceived += self.on_web_resource_response
        sender.CoreWebView2.WebResourceRequested += self.on_web_resource_request

        if self._should_ignore_ssl():
            sender.CoreWebView2.ServerCertificateErrorDetected += self.on_certificate_error

        sender.CoreWebView2.DownloadStarting += self.on_download_starting

        self._apply_settings(sender.CoreWebView2.Settings)

        if _state['private_mode']:
            sender.CoreWebView2.CookieManager.DeleteAllCookies()

        kind, content = self._get_initial_load()
        if kind == 'url':
            self.load_url(content)
        else:
            self.load_html(content, '')

        if _state['debug'] and webview_settings['OPEN_DEVTOOLS_IN_DEBUG']:
            sender.CoreWebView2.OpenDevToolsWindow()

    def on_download_starting(self, sender, args):
        if not self._should_allow_download():
            args.Cancel = True
            return

        dialog = WinForms.SaveFileDialog()
        initial_dir = self._get_download_initial_dir()
        if initial_dir:
            dialog.InitialDirectory = initial_dir
        dialog.Filter = (
            self.pywebview_window.localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
        )
        dialog.RestoreDirectory = True
        dialog.FileName = os.path.basename(args.ResultFilePath)

        result = dialog.ShowDialog(self.form)
        if result == WinForms.DialogResult.OK:
            args.ResultFilePath = dialog.FileName
        else:
            args.Cancel = True

    def on_navigation_start(self, sender, args):
        if self.pywebview_window.transparent:
            self.form.Show()
            self.form.Activate()

    def on_web_resource_response(self, sender, args):
        headers = {header.Key: header.Value for header in args.Response.Headers.GetEnumerator()}
        self._fire_response_event(str(args.Request.Uri), args.Response.StatusCode, headers)

    def on_web_resource_request(self, sender, args):
        original_headers = {
            header.Key: header.Value for header in args.Request.Headers.GetEnumerator()
        }
        diff = self._compute_request_header_diff(
            original_headers, str(args.Request.Uri), args.Request.Method
        )
        if diff is None:
            return
        extra, missing = diff
        for k, v in extra.items():
            args.Request.Headers.SetHeader(k, v)
        for k in missing:
            args.Request.Headers.RemoveHeader(k)

    def on_navigation_completed(self, sender, _):
        url = str(sender.Source)
        self.url = None if self.ishtml else url
        inject_pywebview(renderer, self.pywebview_window)


# Backward-compatible alias used by winforms.py
EdgeChrome = WinFormsEdgeChrome
