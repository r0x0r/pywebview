"""
(C) 2014-2018 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
import sys
import logging
import json
import webbrowser
try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from uuid import uuid1
from threading import Event, Semaphore
from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG, parse_file_type, escape_string, _js_bridge_call
from webview.util import parse_api_js
from webview.js.css import disable_text_select


logger = logging.getLogger('pywebview')

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('WebKit2', '4.0')

from gi.repository import Gtk as gtk
from gi.repository import Gdk
from gi.repository import GLib as glib
from gi.repository import WebKit2 as webkit


class BrowserView:
    instances = {}

    class JSBridge:
        def __init__(self, api_instance, parent_uid):
            self.api = api_instance
            self.uid = uuid1().hex[:8]
            self.parent_uid = parent_uid

        def call(self, func_name, param):
            if param == 'undefined':
                param = None
            return _js_bridge_call(self.parent_uid, self.api, func_name, param)

    def __init__(self, uid, title, url, width, height, resizable, fullscreen, min_size,
                 confirm_quit, background_color, debug, js_api, text_select, frameless, webview_ready):
        BrowserView.instances[uid] = self
        self.uid = uid

        self.webview_ready = webview_ready
        self.is_fullscreen = False
        self.js_results = {}
        self.load_event = Event()
        self.load_event.clear()

        glib.threads_init()
        self.window = gtk.Window(title=title)

        if resizable:
            self.window.set_size_request(min_size[0], min_size[1])
            self.window.resize(width, height)
        else:
            self.window.set_size_request(width, height)

        self.window.set_resizable(resizable)
        self.window.set_position(gtk.WindowPosition.CENTER)

        # Set window background color
        style_provider = gtk.CssProvider()
        style_provider.load_from_data(
            'GtkWindow {{ background-color: {}; }}'.format(background_color).encode()
        )
        gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        scrolled_window = gtk.ScrolledWindow()
        self.window.add(scrolled_window)

        if confirm_quit:
            self.window.connect('delete-event', self.on_destroy)
        else:
            self.window.connect('delete-event', self.close_window)

        if js_api:
            self.js_bridge = BrowserView.JSBridge(js_api, self.uid)
        else:
            self.js_bridge = None

        self.text_select = text_select

        self.webview = webkit.WebView()
        self.webview.connect('notify::visible', self.on_webview_ready)
        self.webview.connect('load_changed', self.on_load_finish)
        self.webview.connect('notify::title', self.on_title_change)
        self.webview.connect('decide-policy', self.on_navigation)

        if frameless:
            self.window.set_decorated(False)
            self.move_progress = False
            self.webview.connect('button-release-event', self.on_mouse_release)
            self.webview.connect('button-press-event', self.on_mouse_press)
            self.window.connect('motion-notify-event', self.on_mouse_move)

        if debug:
            self.webview.get_settings().props.enable_developer_extras = True
        else:
            self.webview.connect('context-menu', lambda a,b,c,d: True) # Disable context menu

        self.webview.set_opacity(0.0)
        scrolled_window.add(self.webview)

        if url is not None:
            self.webview.load_uri(url)
        elif js_api is None:
            self.load_event.set()

        if fullscreen:
            self.toggle_fullscreen()

    def close_window(self, *data):
        for res in self.js_results.values():
            res['semaphore'].release()

        while gtk.events_pending():
            gtk.main_iteration()

        self.window.destroy()
        del BrowserView.instances[self.uid]

        if BrowserView.instances == {}:
            gtk.main_quit()

    def on_destroy(self, widget=None, *data):
        dialog = gtk.MessageDialog(parent=self.window, flags=gtk.DialogFlags.MODAL & gtk.DialogFlags.DESTROY_WITH_PARENT,
                                          type=gtk.MessageType.QUESTION, buttons=gtk.ButtonsType.OK_CANCEL,
                                          message_format=localization['global.quitConfirmation'])
        result = dialog.run()
        if result == gtk.ResponseType.OK:
            self.close_window()

        dialog.destroy()
        return True

    def on_webview_ready(self, arg1, arg2):
        # in webkit2 notify:visible fires after the window was closed and BrowserView object destroyed.
        # for a lack of better solution we check that BrowserView has 'webview_ready' attribute
        if 'webview_ready' in dir(self):
            self.webview_ready.set()

    def on_load_finish(self, webview, status):
        # Show the webview if it's not already visible
        if not webview.props.opacity:
            glib.idle_add(webview.set_opacity, 1.0)

        if status == webkit.LoadEvent.FINISHED:
            if not self.text_select:
                webview.run_javascript(disable_text_select)

            if self.js_bridge:
                self._set_js_api()
            else:
                self.load_event.set()

    def on_title_change(self, webview, title):
        title = webview.get_title()

        try:
            js_data = json.loads(title)

            if 'type' not in js_data:
                return

            elif js_data['type'] == 'eval':  # return result of evaluate_js
                unique_id = js_data['uid']
                result = js_data['result'] if 'result' in js_data else None

                js = self.js_results[unique_id]
                js['result'] = result
                js['semaphore'].release()

            elif js_data['type'] == 'invoke':  # invoke js api's function
                func_name = js_data['function']
                param = js_data['param'] if 'param' in js_data else None
                return_val = self.js_bridge.call(func_name, param)

                # Give back the return value to JS as a string
                code = 'pywebview._bridge.return_val = "{0}";'.format(escape_string(str(return_val)))
                webview.run_javascript(code)

        except ValueError: # Python 2
            pass
        except json.JSONDecodeError: # Python 3
            pass

    def on_navigation(self, webview, decision, decision_type):
        if type(decision) == webkit.NavigationPolicyDecision:
            uri = decision.get_request().get_uri()

            if decision.get_frame_name() == '_blank':
                webbrowser.open(uri, 2, True)
                decision.ignore()

    def on_mouse_release(self, sender, event):
        self.move_progress = False

    def on_mouse_press(self, _, event):
        self.point_diff = [x - y for x, y in zip(self.window.get_position(), [event.x_root, event.y_root])]
        self.move_progress = True

    def on_mouse_move(self, _, event):
        if self.move_progress:
            point = [x + y for x, y in zip((event.x_root, event.y_root), self.point_diff)]
            self.window.move(point[0], point[1])

    def show(self):
        self.window.show_all()

        if gtk.main_level() == 0:
            gtk.main()

    def destroy(self):
        self.window.emit('delete-event', Gdk.Event())

    def set_title(self, title):
        self.window.set_title(title)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.window.unfullscreen()
        else:
            self.window.fullscreen()

        self.is_fullscreen = not self.is_fullscreen

    def set_window_size(self, width, height):
        self.window.resize(width, height)

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_types):
        if dialog_type == FOLDER_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.SELECT_FOLDER
            title = localization['linux.openFolder']
            button = gtk.STOCK_OPEN
        elif dialog_type == OPEN_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.OPEN
            if allow_multiple:
                title = localization['linux.openFiles']
            else:
                title = localization['linux.openFile']

            button = gtk.STOCK_OPEN
        elif dialog_type == SAVE_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.SAVE
            title = localization['global.saveFile']
            button = gtk.STOCK_SAVE

        dialog = gtk.FileChooserDialog(title, self.window, gtk_dialog_type,
                                       (gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL, button, gtk.ResponseType.OK))

        dialog.set_select_multiple(allow_multiple)
        dialog.set_current_folder(directory)
        self._add_file_filters(dialog, file_types)

        if dialog_type == SAVE_DIALOG:
            dialog.set_current_name(save_filename)

        response = dialog.run()

        if response == gtk.ResponseType.OK:
            file_name = dialog.get_filenames()
        else:
            file_name = None

        dialog.destroy()

        return file_name

    def _add_file_filters(self, dialog, file_types):
        for s in file_types:
            description, extensions = parse_file_type(s)

            f = gtk.FileFilter()
            f.set_name(description)
            for e in extensions.split(';'):
                f.add_pattern(e)

            dialog.add_filter(f)

    def get_current_url(self):
        self.load_event.wait()
        uri = self.webview.get_uri()
        return uri

    def load_url(self, url):
        self.load_event.clear()
        self.webview.load_uri(url)

    def load_html(self, content, base_uri):
        self.load_event.clear()
        self.webview.load_html(content, base_uri)

    def evaluate_js(self, script):
        def _evaluate_js():
            self.webview.run_javascript(code, None, None, None)

        unique_id = uuid1().hex
        result_semaphore = Semaphore(0)
        self.js_results[unique_id] = {'semaphore': result_semaphore, 'result': None}

        code = 'document.title = JSON.stringify({{"type": "eval", "uid": "{0}", "result": {1}}})'.format(unique_id, script)

        self.load_event.wait()
        glib.idle_add(_evaluate_js)
        result_semaphore.acquire()

        if not gtk.main_level():
            # Webview has been closed, don't proceed
            return None

        result = self.js_results[unique_id]['result']

        result = None if result == 'undefined' or result == 'null' or result is None else result if result == '' else json.loads(result)

        del self.js_results[unique_id]

        return result

    def _set_js_api(self):
        def create_bridge():
            # Make the `call` method write the function name and param to the
            # `status` attribute of the JS window, delimited by a unique token.
            # The return value will be passed back to the `return_val` attribute
            # of the bridge by the on_status_change handler.
            code = """
            window.pywebview._bridge.call = function(funcName, param) {{
                document.title = JSON.stringify({{"type": "invoke", "uid": "{0}", "function": funcName, "param": param}})
                return this.return_val;
            }};""".format(self.js_bridge.uid)

            # Create the `pywebview` JS api object
            self.webview.run_javascript(parse_api_js(self.js_bridge.api))
            self.webview.run_javascript(code)
            self.load_event.set()

        glib.idle_add(create_bridge)


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, text_select, frameless, webview_ready):
    def create():
        browser = BrowserView(uid, title, url, width, height, resizable, fullscreen, min_size,
                              confirm_quit, background_color, debug, js_api, text_select, frameless, webview_ready)
        browser.show()

    if uid == 'master':
        create()
    else:
        glib.idle_add(create)


def set_title(title, uid):
    def _set_title():
        BrowserView.instances[uid].set_title(title)
    glib.idle_add(_set_title)    


def destroy_window(uid):
    def _destroy_window():
        BrowserView.instances[uid].close_window()
    glib.idle_add(_destroy_window)


def toggle_fullscreen(uid):
    def _toggle_fullscreen():
        BrowserView.instances[uid].toggle_fullscreen()
    glib.idle_add(_toggle_fullscreen)


def set_window_size(width, height, uid):
    def _set_window_size():
        BrowserView.instances[uid].set_window_size(width,height)
    glib.idle_add(_set_window_size)


def get_current_url(uid):
    return BrowserView.instances[uid].get_current_url()


def load_url(url, uid):
    def _load_url():
        BrowserView.instances[uid].load_url(url)
    glib.idle_add(_load_url)


def load_html(content, base_uri, uid):
    def _load_html():
        BrowserView.instances[uid].load_html(content, base_uri)
    glib.idle_add(_load_html)


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types):
    i = list(BrowserView.instances.values())[0]     # arbitary instance
    file_name_semaphore = Semaphore(0)
    file_names = []

    def _create():
        result = i.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types)
        if result is None:
            file_names.append(None)
        else:
            result = map(unicode, result) if sys.version < '3' else result
            file_names.append(tuple(result))

        file_name_semaphore.release()

    glib.idle_add(_create)
    file_name_semaphore.acquire()

    return file_names[0]


def evaluate_js(script, uid):
    return BrowserView.instances[uid].evaluate_js(script)
