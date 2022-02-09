# -*- coding: utf-8 -*-

"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
import json
import shutil
import tempfile
import webbrowser
from threading import Event, Semaphore
from ctypes import windll

from webview import WebViewException, _debug, _user_agent
from webview.serving import resolve_url
from webview.util import parse_api_js, interop_dll_path, parse_file_type, inject_base_uri, default_html, js_bridge_call
from webview.js import alert
from webview.js.css import disable_text_select

import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type, Environment, Uri
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF

clr.AddReference(interop_dll_path('Microsoft.Toolkit.Forms.UI.Controls.WebView.dll'))
from Microsoft.Toolkit.Forms.UI.Controls import WebView
from System.ComponentModel import ISupportInitialize

logger = logging.getLogger('pywebview')

class EdgeHTML:
    def __init__(self, form, window):
        self.pywebview_window = window
        self.web_view = WebView()

        life = ISupportInitialize(self.web_view)
        life.BeginInit()
        form.Controls.Add(self.web_view)

        self.js_results = {}
        self.js_result_semaphore = Semaphore(0)
        self.web_view.Dock = WinForms.DockStyle.Fill
        self.web_view.DpiAware = True
        self.web_view.IsIndexedDBEnabled = True
        self.web_view.IsJavaScriptEnabled = True
        self.web_view.IsScriptNotifyAllowed = True
        self.web_view.IsPrivateNetworkClientServerCapabilityEnabled = True
        self.web_view.DefaultBackgroundColor = form.BackColor

        self.web_view.ScriptNotify += self.on_script_notify
        self.web_view.NewWindowRequested += self.on_new_window_request
        self.web_view.NavigationCompleted += self.on_navigation_completed

        # This must be before loading URL. Otherwise the webview will remain empty
        life.EndInit()

        self.httpd = None # HTTP server for load_html
        self.tmpdir = None
        self.url = None
        self.ishtml = False

        if window.html or 'localhost' in window.real_url or '127.0.0.1' in window.real_url:
            _allow_localhost()

        if window.real_url:
            self.load_url(window.real_url)
        elif window.html:
            self.load_html(window.html, '')
        else:
            self.load_html(default_html, '')

    def evaluate_js(self, script, id):
        try:
            result = self.web_view.InvokeScript('eval', (script,))
        except Exception as e:
            logger.exception('Error occurred in script')
            result = None

        self.js_results[id] = None if result is None or result == '' else json.loads(result)
        self.js_result_semaphore.release()

    def get_current_url(self):
        return self.url

    def load_html(self, html, base_uri):
        self.tmpdir = tempfile.mkdtemp()
        self.temp_html = os.path.join(self.tmpdir, 'index.html')

        with open(self.temp_html, 'w', encoding='utf-8') as f:
            f.write(inject_base_uri(html, base_uri))

        if self.httpd:
            self.httpd.shutdown()

        url = resolve_url('file://' + self.temp_html, True)
        self.ishtml = True
        self.web_view.Navigate(url)

    def load_url(self, url):
        self.ishtml = False

        # WebViewControl as of 5.1.1 crashes on file:// urls. Stupid workaround to make it work
        if url.startswith('file://'):
            url = resolve_url(url, True)

        self.web_view.Navigate(url)

    def on_script_notify(self, _, args):
        try:
            func_name, func_param, value_id = json.loads(args.Value)

            if func_name == 'alert':
                WinForms.MessageBox.Show(func_param)
            elif func_name == 'console':
                print(func_param)
            else:
                js_bridge_call(self.pywebview_window, func_name, func_param, value_id)
        except Exception as e:
            logger.exception('Exception occured during on_script_notify')

    def on_new_window_request(self, _, args):
        webbrowser.open(str(args.get_Uri()))
        args.set_Handled(True)

    def on_navigation_completed(self, _, args):
        try:
            if self.tmpdir and os.path.exists(self.tmpdir):
                shutil.rmtree(self.tmpdir)
                self.tmpdir = None
        except Exception as e:
            logger.exception('Failed deleting %s' % self.tmpdir)

        url = str(args.Uri)
        self.url = None if self.ishtml else url
        self.web_view.InvokeScript('eval', ('window.alert = (msg) => window.external.notify(JSON.stringify(["alert", msg+"", ""]))',))

        if _debug['mode']:
            self.web_view.InvokeScript('eval', ('window.console = { log: (msg) => window.external.notify(JSON.stringify(["console", msg+"", ""]))}',))

        self.web_view.InvokeScript('eval', (parse_api_js(self.pywebview_window, 'edgehtml'),))

        if not self.pywebview_window.text_select:
            self.web_view.InvokeScript('eval', (disable_text_select,))

        self.pywebview_window.events.loaded.set()

def _allow_localhost():
    import subprocess

    # lifted from https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
    def subprocess_args(include_stdout=True):
        if hasattr(subprocess, 'STARTUPINFO'):
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            env = os.environ
        else:
            si = None
            env = None

        if include_stdout:
            ret = {'stdout': subprocess.PIPE}
        else:
            ret = {}

        ret.update({'stdin': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'startupinfo': si,
                    'env': env })
        return ret

    output = subprocess.check_output('checknetisolation LoopbackExempt -s', **subprocess_args(False))

    if 'cw5n1h2txyewy' not in str(output):
        windll.shell32.ShellExecuteW(None, 'runas', 'checknetisolation', 'LoopbackExempt -a -n=\"Microsoft.Win32WebViewHost_cw5n1h2txyewy\"', None, 1)


