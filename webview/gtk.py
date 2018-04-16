"""
(C) 2014-2018 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
import sys
import logging
import json
import webbrowser

from uuid import uuid1
from threading import Event, Semaphore, Lock
from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG, parse_file_type, escape_string, _js_bridge_call
from webview.util import parse_api_js
from webview.js.css import disable_text_select


logger = logging.getLogger(__name__)

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('WebKit', '3.0')

from gi.repository import Gtk as gtk
from gi.repository import Gdk
from gi.repository import GLib as glib
from gi.repository import WebKit as webkit


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
                 confirm_quit, background_color, debug, js_api, text_select, webview_ready):
        BrowserView.instances[uid] = self
        self.uid = uid

        self.webview_ready = webview_ready
        self.is_fullscreen = False
        self.js_result_semaphores = []
        self.eval_js_lock = Lock()
        self.load_event = Event()

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
        self.webview.connect('document-load-finished', self.on_load_finish)
        self.webview.connect('status-bar-text-changed', self.on_status_change)
        self.webview.connect('new-window-policy-decision-requested', self.on_new_window_request)

        if debug:
            self.webview.props.settings.props.enable_developer_extras = True
            self.webview.get_inspector().connect('inspect-web-view', self.on_inspect_webview)
        else:
            self.webview.props.settings.props.enable_default_context_menu = False

        self.webview.props.settings.props.javascript_can_access_clipboard = True
        self.webview.props.opacity = 0.0
        scrolled_window.add(self.webview)

        if url is not None:
            self.webview.load_uri(url)
        else:
            self.load_event.set()

        if fullscreen:
            self.toggle_fullscreen()

    def close_window(self, *data):
        while gtk.events_pending():
            gtk.main_iteration()

        self.window.destroy()
        del BrowserView.instances[self.uid]

        try:    # Close inspector if open
            BrowserView.instances[self.uid + '-inspector'].window.destroy()
            del BrowserView.instances[self.uid + '-inspector']
        except KeyError:
            pass

        if BrowserView.instances == {}:
            gtk.main_quit()

        for s in self.js_result_semaphores:
            s.release()

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
        glib.idle_add(self.webview_ready.set)

    def on_load_finish(self, webview, webframe):
        # Show the webview if it's not already visible
        if not webview.props.opacity:
            glib.idle_add(webview.set_opacity, 1.0)

        if not self.text_select:
            webview.execute_script(disable_text_select)

        if self.js_bridge:
            self._set_js_api()
        else:
            self.load_event.set()

    def on_status_change(self, webview, status):
        try:
            delim = '_' + self.js_bridge.uid + '_'
        except AttributeError:
            return

        # Check if status was updated by a JSBridge call
        if status.startswith(delim):
            _, func_name, param = status.split(delim)
            return_val = self.js_bridge.call(func_name, param)
            # Give back the return value to JS as a string
            code = 'pywebview._bridge.return_val = "{0}";'.format(escape_string(str(return_val)))
            webview.execute_script(code)

    def on_inspect_webview(self, inspector, webview):
        title = 'Web Inspector - {}'.format(self.window.get_title())
        uid = self.uid + '-inspector'

        inspector = BrowserView(uid, title, '', 700, 500, True, False, (300,200),
                                False, '#fff', False, None, self.webview_ready)
        inspector.show()
        return inspector.webview

    def on_new_window_request(self, webview, frame, request, action, decision, *data):
        if action.get_target_frame() == '_blank':
            webbrowser.open(request.get_uri(), 2, True)
        decision.ignore()

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
        self.webview.load_string(content, 'text/html', 'utf-8', base_uri)

    def evaluate_js(self, script):
        def _evaluate_js():
            self.webview.execute_script(code)
            result_semaphore.release()

        self.eval_js_lock.acquire()
        result_semaphore = Semaphore(0)
        self.js_result_semaphores.append(result_semaphore)
        # Backup the doc title and store the result in it with a custom prefix
        unique_id = uuid1().hex
        code = 'window.oldTitle{0} = document.title; document.title = {1};'.format(unique_id, script)

        self.load_event.wait()
        glib.idle_add(_evaluate_js)
        result_semaphore.acquire()

        if not gtk.main_level():
            # Webview has been closed, don't proceed
            return None

        result = self.webview.get_title()
        result = None if result == 'undefined' or result == 'null' else result if result == '' else json.loads(result)

        # Restore document title and return
        code = 'document.title = window.oldTitle{0}'.format(unique_id)
        glib.idle_add(_evaluate_js)
        self.js_result_semaphores.remove(result_semaphore)
        self.eval_js_lock.release()

        return result


    def _set_js_api(self):
        def create_bridge():
            # Make the `call` method write the function name and param to the
            # `status` attribute of the JS window, delimited by a unique token.
            # The return value will be passed back to the `return_val` attribute
            # of the bridge by the on_status_change handler.
            code = """
            window.pywebview._bridge.call = function(funcName, param) {{
                window.status = "_{0}_" + funcName + "_{0}_" + param;
                return this.return_val;
            }};""".format(self.js_bridge.uid)

            # Create the `pywebview` JS api object
            self.webview.execute_script(parse_api_js(self.js_bridge.api))
            self.webview.execute_script(code)
            self.load_event.set()

        glib.idle_add(create_bridge)


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, text_select, webview_ready):
    def create():
        browser = BrowserView(uid, title, url, width, height, resizable, fullscreen, min_size,
                              confirm_quit, background_color, debug, js_api, text_select, webview_ready)
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
