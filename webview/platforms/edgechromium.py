import json
import logging
import os
import webbrowser
import winreg
from threading import Semaphore

import clr

from webview import _settings, settings as webview_settings
from webview.dom import _dnd_state
from webview.js.css import disable_text_select
from webview.util import DEFAULT_HTML, create_cookie, interop_dll_path, js_bridge_call, inject_pywebview

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import Action, Func, String, Type, Uri
from System.Collections.Generic import List
from System.Drawing import Color
from System.Globalization import CultureInfo
from System.Threading.Tasks import Task, TaskScheduler

clr.AddReference(interop_dll_path('Microsoft.Web.WebView2.Core.dll'))
clr.AddReference(interop_dll_path('Microsoft.Web.WebView2.WinForms.dll'))

from Microsoft.Web.WebView2.Core import CoreWebView2Cookie, CoreWebView2ServerCertificateErrorAction
from Microsoft.Web.WebView2.WinForms import CoreWebView2CreationProperties, WebView2

for platform in ('win-arm64', 'win-x64', 'win-x86'):
    os.environ['Path'] += ';' + interop_dll_path(platform)


logger = logging.getLogger('pywebview')


class EdgeChrome:
    def __init__(self, form, window, cache_dir):
        self.pywebview_window = window
        self.web_view = WebView2()
        props = CoreWebView2CreationProperties()
        props.UserDataFolder = cache_dir
        props.set_IsInPrivateModeEnabled(_settings['private_mode'])
        props.AdditionalBrowserArguments = '--disable-features=ElasticOverscroll'

        if webview_settings['ALLOW_FILE_URLS']:
            props.AdditionalBrowserArguments += ' --allow-file-access-from-files'

        self.web_view.CreationProperties = props

        self.form = form
        form.Controls.Add(self.web_view)

        self.js_results = {}
        self.js_result_semaphore = Semaphore(0)
        self.web_view.Dock = WinForms.DockStyle.Fill
        self.web_view.BringToFront()
        self.web_view.CoreWebView2InitializationCompleted += self.on_webview_ready
        self.web_view.NavigationStarting += self.on_navigation_start
        self.web_view.NavigationCompleted += self.on_navigation_completed
        self.web_view.WebMessageReceived += self.on_script_notify
        self.syncContextTaskScheduler = TaskScheduler.FromCurrentSynchronizationContext()
        self.web_view.DefaultBackgroundColor = Color.FromArgb(255, int(window.background_color.lstrip("#")[0:2], 16), int(window.background_color.lstrip("#")[2:4], 16), int(window.background_color.lstrip("#")[4:6], 16))

        if window.transparent:
            self.web_view.DefaultBackgroundColor = Color.Transparent

        self.url = None
        self.ishtml = False
        self.html = DEFAULT_HTML
        self.web_view.EnsureCoreWebView2Async(None)

    def evaluate_js(self, script, semaphore, js_result, callback=None):
        def _callback(result):
            if callback is None:
                result = None if result is None or result == '' else json.loads(result)
                js_result.append(result)
                semaphore.release()
            else:
                # future js callback option to handle async js method
                callback(result)
                js_result.append(None)
                semaphore.release()

        try:
            self.web_view.ExecuteScriptAsync(script).ContinueWith(
                Action[Task[String]](lambda task: _callback(json.loads(task.Result))),
                self.syncContextTaskScheduler,
            )
        except Exception:
            logger.exception('Error occurred in script')
            js_result.append(None)
            semaphore.release()

    def clear_cookies(self):
        self.web_view.CoreWebView2.CookieManager.DeleteAllCookies()

    def get_cookies(self, cookies, semaphore):
        def _callback(task):
            for c in task.Result:
                _cookies.append(c)

            self.web_view.Invoke(Func[Type](_parse_cookies))

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
        self.web_view.CoreWebView2.CookieManager.GetCookiesAsync(self.url).ContinueWith(
            Action[Task[List[CoreWebView2Cookie]]](_callback), self.syncContextTaskScheduler
        )

    def get_current_url(self):
        return self.url

    def load_html(self, content, _):
        self.html = content
        self.ishtml = True
        self.pywebview_window.events.loaded.clear()

        if self.web_view.CoreWebView2:
            self.web_view.CoreWebView2.NavigateToString(self.html)
        else:
            self.web_view.EnsureCoreWebView2Async(None)

    def load_url(self, url):
        self.ishtml = False
        self.web_view.Source = Uri(url)

    def on_certificate_error(self, _, args):
        args.set_Action(CoreWebView2ServerCertificateErrorAction.AlwaysAllow)

    def on_script_notify(self, _, args):
        try:
            return_value = args.get_WebMessageAsJson()

            if return_value == '"FilesDropped"':
                if _dnd_state['num_listeners'] == 0:
                    return

                files = [
                    (os.path.basename(file.Path), file.Path)
                    for file
                    in list(args.get_AdditionalObjects())
                    if 'CoreWebView2File' in str(type(file))
                ]
                _dnd_state['paths'] += files
                return

            func_name, func_param, value_id = json.loads(return_value)
            func_param = json.loads(func_param)
            if func_name == 'alert':
                WinForms.MessageBox.Show(func_param)
            elif func_name == 'console':
                print(func_param)
            else:
                js_bridge_call(self.pywebview_window, func_name, func_param, value_id)
        except Exception:
            logger.exception('Exception occurred during on_script_notify')

    def on_new_window_request(self, sender, args):
        args.set_Handled(True)

        if webview_settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']:
            webbrowser.open(str(args.get_Uri()))
        else:
            self.load_url(str(args.get_Uri()))

    def on_webview_ready(self, sender, args):
        if not args.IsSuccess:
            logger.error(
                'WebView2 initialization failed with exception:\n '
                + str(args.InitializationException)
            )
            return

        sender.CoreWebView2.NewWindowRequested += self.on_new_window_request

        if _settings['ssl']:
            sender.CoreWebView2.ServerCertificateErrorDetected += self.on_certificate_error

        sender.CoreWebView2.DownloadStarting += self.on_download_starting

        settings = sender.CoreWebView2.Settings
        settings.AreBrowserAcceleratorKeysEnabled = _settings['debug']
        settings.AreDefaultContextMenusEnabled = _settings['debug']
        settings.AreDefaultScriptDialogsEnabled = True
        settings.AreDevToolsEnabled = _settings['debug']
        settings.IsBuiltInErrorPageEnabled = True
        settings.IsScriptEnabled = True
        settings.IsWebMessageEnabled = True
        settings.IsStatusBarEnabled = _settings['debug']
        settings.IsSwipeNavigationEnabled = False
        settings.IsZoomControlEnabled = True

        if _settings['user_agent']:
            settings.UserAgent = _settings['user_agent']

        if _settings['private_mode']:
            # cookies persist even if UserDataFolder is in memory. We have to delete cookies manually.
            sender.CoreWebView2.CookieManager.DeleteAllCookies()

        if self.pywebview_window.real_url:
            self.load_url(self.pywebview_window.real_url)
        elif self.pywebview_window.html:
            self.html = self.pywebview_window.html
            self.load_html(self.pywebview_window.html, '')
        else:
            self.load_html(DEFAULT_HTML, '')

        if _settings['debug'] and webview_settings['OPEN_DEVTOOLS_IN_DEBUG']:
            sender.CoreWebView2.OpenDevToolsWindow()

    def on_download_starting(self, sender, args):
        if not webview_settings['ALLOW_DOWNLOADS']:
            args.Cancel = True
            return

        dialog = WinForms.SaveFileDialog()

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as windows_key:
                dialog.InitialDirectory = winreg.QueryValueEx(windows_key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        except Exception as e:
            logger.exception(e)

        dialog.Filter = self.pywebview_window.localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
        dialog.RestoreDirectory = True
        dialog.FileName = os.path.basename(args.ResultFilePath)

        result = dialog.ShowDialog(self.form)
        if result == WinForms.DialogResult.OK:
            args.ResultFilePath = dialog.FileName
        else:
            args.Cancel = True

    def on_navigation_start(self, sender, args):
        pass

    def on_navigation_completed(self, sender, _):
        url = str(sender.Source)
        self.url = None if self.ishtml else url

        self.web_view.ExecuteScriptAsync(inject_pywebview(self.pywebview_window, 'chromium'))

        if not self.pywebview_window.text_select:
            self.web_view.ExecuteScriptAsync(disable_text_select)

        self.pywebview_window.events.loaded.set()
