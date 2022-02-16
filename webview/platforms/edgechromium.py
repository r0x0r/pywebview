# -*- coding: utf-8 -*-

"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import logging
import json
import webbrowser
from threading import Semaphore
from ctypes import windll
from platform import architecture

from webview import _debug, _user_agent
from webview.serving import resolve_url
from webview.util import parse_api_js, interop_dll_path, parse_file_type, inject_base_uri, default_html, js_bridge_call
from webview.js import alert
from webview.js.css import disable_text_select

import clr


clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, String, Action, Func, Type, Environment, Uri
from System.Threading.Tasks import Task, TaskScheduler, TaskContinuationOptions
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF

archpath = 'x64' if architecture()[0] == '64bit' else 'x86'
os.environ['Path'] = interop_dll_path(archpath) + ';' + os.environ['Path']
clr.AddReference(interop_dll_path('Microsoft.Web.WebView2.Core.dll'))
clr.AddReference(interop_dll_path('Microsoft.Web.WebView2.WinForms.dll'))
from Microsoft.Web.WebView2.WinForms import WebView2, CoreWebView2CreationProperties
from Microsoft.Web.WebView2.Core import CoreWebView2Environment

logger = logging.getLogger('pywebview')

class EdgeChrome:
    def __init__(self, form, window):
        self.pywebview_window = window
        self.web_view = WebView2()
        props = CoreWebView2CreationProperties()
        #props.UserDataFolder = os.path.join(os.getcwd(), 'profile')
        props.UserDataFolder = os.path.join(os.environ['LOCALAPPDATA'], 'pywebview')
        self.web_view.CreationProperties = props
        form.Controls.Add(self.web_view)

        self.js_results = {}
        self.js_result_semaphore = Semaphore(0)
        self.web_view.Dock = WinForms.DockStyle.Fill

        self.web_view.CoreWebView2InitializationCompleted += self.on_webview_ready
        self.web_view.NavigationStarting += self.on_navigation_start
        self.web_view.NavigationCompleted += self.on_navigation_completed
        self.web_view.WebMessageReceived += self.on_script_notify

        if window.transparent:
            self.web_view.DefaultBackgroundColor = Color.Transparent

        self.url = None
        self.ishtml = False
        self.html = None

        if window.real_url:
            self.load_url(window.real_url)
        elif window.html:
            self.html = window.html
            self.load_html(window.html, '')
        else:
            self.html = default_html
            self.load_html(default_html, '')

    def evaluate_js(self, script, id, callback=None):
        def _callback(result):
            if callback is None:
                self.js_results[id] = None if result is None or result == '' else json.loads(result)
                self.js_result_semaphore.release()
            else:
                # future js callback option to handle async js method
                callback(result)
                self.js_results[id] = None
                self.js_result_semaphore.release()

        self.syncContextTaskScheduler = TaskScheduler.FromCurrentSynchronizationContext()
        try:
            result = self.web_view.ExecuteScriptAsync(script).ContinueWith(
            Action[Task[String]](
                lambda task: _callback(json.loads(task.Result))
            ),
            self.syncContextTaskScheduler)
        except Exception as e:
            logger.exception('Error occurred in script')
            self.js_results[id] = None
            self.js_result_semaphore.release()

    def get_current_url(self):
        return self.url

    def load_html(self, content, base_uri):
        self.html = content
        self.ishtml = True
        if self.web_view.CoreWebView2:
            self.web_view.CoreWebView2.NavigateToString(self.html)
        else:
            self.web_view.EnsureCoreWebView2Async(None)

    def load_url(self, url):
        self.ishtml = False
        self.web_view.Source = Uri(url)

    def on_script_notify(self, _, args):
        try:
            return_value = args.get_WebMessageAsJson()
            func_name, func_param, value_id = json.loads(return_value)
            if func_name == 'alert':
                WinForms.MessageBox.Show(func_param)
            elif func_name == 'console':
                print(func_param)
            else:
                js_bridge_call(self.pywebview_window, func_name, func_param, value_id)
        except Exception as e:
            logger.exception('Exception occured during on_script_notify')

    def on_new_window_request(self, _, args):
        args.set_Handled(True)
        webbrowser.open(str(args.get_Uri()))

    def on_webview_ready(self, sender, args):
        sender.CoreWebView2.NewWindowRequested += self.on_new_window_request
        settings = sender.CoreWebView2.Settings
        settings.AreDefaultContextMenusEnabled = _debug['mode']
        settings.AreDefaultScriptDialogsEnabled = True
        settings.AreDevToolsEnabled = _debug['mode']
        settings.IsBuiltInErrorPageEnabled = True
        settings.IsScriptEnabled = True
        settings.IsWebMessageEnabled = True
        settings.IsStatusBarEnabled = _debug['mode']
        settings.IsZoomControlEnabled = True

        if _user_agent:
            settings.UserAgent = _user_agent

        if self.html:
            sender.CoreWebView2.NavigateToString(self.html)

    def on_navigation_start(self, sender, args):
        pass

    def on_navigation_completed(self, sender, args):
        url = str(sender.Source)
        self.url = None if self.ishtml else url

        self.web_view.ExecuteScriptAsync(parse_api_js(self.pywebview_window, 'chromium'))

        if not self.pywebview_window.text_select:
            self.web_view.ExecuteScriptAsync(disable_text_select)

        self.pywebview_window.events.loaded.set()
