import json
import logging
import os
import webbrowser
from threading import Semaphore, Thread, main_thread
from typing import Any
from uuid import uuid1

from webview import (FOLDER_DIALOG, OPEN_DIALOG, SAVE_DIALOG, _settings, settings,
                     parse_file_type, windows)
from webview.dom import _dnd_state
from webview.js.css import disable_text_select
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.screen import Screen
from webview.util import DEFAULT_HTML, create_cookie, js_bridge_call, inject_pywebview
from webview.window import FixPoint, Window

logger = logging.getLogger('pywebview')
os.environ['EGL_LOG_LEVEL'] = 'fatal'

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

try:
    gi.require_version('WebKit2', '4.1')
    gi.require_version('Soup', '3.0')
except ValueError:
    logger.debug('WebKit2 4.1 not found. Using 4.0.')
    gi.require_version('WebKit2', '4.0')
    gi.require_version('Soup', '2.4')

from gi.repository import Gdk, Gio
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk
from gi.repository import Soup
from gi.repository import WebKit2 as webkit

renderer = 'gtkwebkit2'
webkit_ver = webkit.get_major_version(), webkit.get_minor_version(), webkit.get_micro_version()

_app = None
_app_actions = {}  # action_label: function


class BrowserView:
    instances = {}

    class JSBridge:
        def __init__(self, window: Window) -> None:
            self.window = window
            self.uid = uuid1().hex[:8]

        def call(self, func_name: str, param: Any, value_id: str):
            if param == 'undefined':
                param = None
            return js_bridge_call(self.window, func_name, param, value_id)

    def __init__(self, window: Window) -> None:
        # Note: _app won't be None because BrowserView() is called after _app is made in `create_window`
        global _app

        BrowserView.instances[window.uid] = self
        self.uid = window.uid
        self.pywebview_window = window

        self.is_fullscreen = False
        self.js_results = {}

        self.window = gtk.ApplicationWindow(title=window.title, application=_app)

        self.shown = window.events.shown
        self.loaded = window.events.loaded

        self.localization = window.localization

        self._last_width = window.initial_width
        self._last_height = window.initial_height

        if window.screen:
            self.screen = window.screen.frame
        else:
            display = Gdk.Display.get_default()
            monitor = Gdk.Display.get_monitor(display, 0)
            self.screen = Gdk.Monitor.get_geometry(monitor)

        if window.resizable:
            self.window.set_size_request(window.min_size[0], window.min_size[1])
            self.window.resize(window.initial_width, window.initial_height)
        else:
            self.window.set_size_request(window.initial_width, window.initial_height)

        if window.maximized:
            self.window.maximize()
        elif window.minimized:
            self.window.iconify()

        if window.initial_x is not None and window.initial_y is not None:
            self.move(window.initial_x, window.initial_y)
        else:
            window_width, window_height = self.window.get_size()
            x = (self.screen.width - window_width) // 2
            y = (self.screen.height - window_height) // 2
            self.move(x, y)

        self.window.set_resizable(window.resizable)
        self.window.set_accept_focus(window.focus)

        # Set window background color
        style_provider = gtk.CssProvider()
        style_provider.load_from_data(
            'GtkWindow {{ background-color: {}; }}'.format(window.background_color).encode()
        )
        gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), style_provider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.NEVER)
        self.window.add(scrolled_window)

        self.window.connect('delete-event', self.close_window)

        self.window.connect('window-state-event', self.on_window_state_change)
        self.window.connect('size-allocate', self.on_window_resize)
        self.window.connect('configure-event', self.on_window_configure)

        self.js_bridge = BrowserView.JSBridge(window)
        self.text_select = window.text_select

        storage_path = _settings['storage_path'] or os.path.join(os.path.expanduser('~'), '.pywebview')

        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

        web_context = webkit.WebContext.get_default()
        self.cookie_manager = web_context.get_cookie_manager()

        if not _settings['private_mode']:
            self.cookie_manager.set_persistent_storage(
                os.path.join(storage_path, 'cookies'), webkit.CookiePersistentStorage.SQLITE
            )

        self.manager = webkit.UserContentManager()
        self.manager.register_script_message_handler('jsBridge')
        self.manager.connect('script-message-received', self.on_js_bridge_call)

        self.webview = webkit.WebView().new_with_user_content_manager(self.manager)
        self.webview.connect('notify::visible', self.on_webview_ready)
        self.webview.connect('load_changed', self.on_load_finish)
        self.webview.connect('decide-policy', self.on_navigation)
        self.webview.connect('drag-data-received', self.on_drag_data)

        if settings['ALLOW_DOWNLOADS']:
            web_context.connect('download-started', self.on_download_started)

        webkit_settings = self.webview.get_settings().props
        user_agent = settings.get('user_agent') or _settings['user_agent']
        if user_agent:
            webkit_settings.user_agent = user_agent

        webkit_settings.enable_media_stream = True
        webkit_settings.enable_mediasource = True
        webkit_settings.enable_webaudio = True
        webkit_settings.enable_webgl = True
        webkit_settings.javascript_can_access_clipboard = True
        webkit_settings.allow_file_access_from_file_urls = settings['ALLOW_FILE_URLS']

        if window.frameless:
            self.window.set_decorated(False)
            if window.easy_drag:
                self.move_progress = False
                self.webview.connect('button-release-event', self.on_mouse_release)
                self.webview.connect('button-press-event', self.on_mouse_press)
                self.window.connect('motion-notify-event', self.on_mouse_move)

        if window.on_top:
            self.window.set_keep_above(True)

        self.transparent = window.transparent
        if window.transparent:
            configure_transparency(self.window)
            configure_transparency(self.webview)
            wvbg = self.webview.get_background_color()
            wvbg.alpha = 0.0
            self.webview.set_background_color(wvbg)

        if _settings['debug']:
            webkit_settings.enable_developer_extras = True

            if settings['OPEN_DEVTOOLS_IN_DEBUG']:
                self.webview.get_inspector().show()
        else:
            self.webview.connect('context-menu', lambda a, b, c, d: True)  # Disable context menu

        if _settings['private_mode']:
            webkit_settings.enable_html5_database = False
            webkit_settings.enable_html5_local_storage = False

        self.webview.set_opacity(0.0)
        scrolled_window.add(self.webview)

        if window.real_url is not None:
            self.webview.load_uri(window.real_url)
        elif window.html:
            self.webview.load_html(window.html, '')
        else:
            self.webview.load_html(DEFAULT_HTML, '')

        if window.fullscreen:
            self.toggle_fullscreen()

    def close_window(self, *data):
        should_cancel = self.pywebview_window.events.closing.set()

        if should_cancel:
            return True

        if self.pywebview_window.confirm_close:
            dialog = gtk.MessageDialog(
                parent=self.window,
                flags=gtk.DialogFlags.MODAL & gtk.DialogFlags.DESTROY_WITH_PARENT,
                type=gtk.MessageType.QUESTION,
                buttons=gtk.ButtonsType.OK_CANCEL,
                message_format=self.localization['global.quitConfirmation'],
            )
            result = dialog.run()
            dialog.destroy()
            if result == gtk.ResponseType.CANCEL:
                return True

        for res in self.js_results.values():
            res['semaphore'].release()

        self.window.destroy()
        del BrowserView.instances[self.uid]

        if self.pywebview_window in windows:
            windows.remove(self.pywebview_window)

        self.pywebview_window.events.closed.set()

        return False

    def on_drag_data(self, widget, drag_context, x, y, data, info, time):
        if _dnd_state['num_listeners'] > 0 and data.get_text():
            files = [
                (os.path.basename(value), value.replace('file://', ''))
                for value
                in data.get_text().split('\n')
                if value.startswith('file://')
            ]
            _dnd_state['paths'] += files

        return False

    def on_window_state_change(self, window, window_state):
        if window_state.changed_mask == Gdk.WindowState.ICONIFIED:
            if (
                Gdk.WindowState.ICONIFIED & window_state.new_window_state
                == Gdk.WindowState.ICONIFIED
            ):
                self.pywebview_window.events.minimized.set()
            else:
                self.pywebview_window.events.restored.set()

        elif window_state.changed_mask == Gdk.WindowState.MAXIMIZED:
            if (
                Gdk.WindowState.MAXIMIZED & window_state.new_window_state
                == Gdk.WindowState.MAXIMIZED
            ):
                self.pywebview_window.events.maximized.set()
            else:
                self.pywebview_window.events.restored.set()

    def on_js_bridge_call(self, manager, message):
        body = json.loads(message.get_js_value().to_string())
        js_bridge_call(self.pywebview_window, body['funcName'], body['params'], body['id'])

    def on_window_resize(self, window, allocation):
        if allocation.width != self._last_width or allocation.height != self._last_height:
            self._last_width = allocation.width
            self._last_height = allocation.height
            self.pywebview_window.events.resized.set(allocation.width, allocation.height)

    def on_window_configure(self, window, event):
        self.pywebview_window.events.moved.set(event.x, event.y)

    def on_webview_ready(self, arg1, arg2):
        # in webkit2 notify:visible fires after the window was closed and BrowserView object destroyed.
        # for a lack of better solution we check that BrowserView has 'webview_ready' attribute
        if 'shown' in dir(self):
            self.shown.set()

    def on_load_finish(self, webview, status):
        # Show the webview if it's not already visible
        if not webview.props.opacity:
            glib.idle_add(webview.set_opacity, 1.0)

        if status == webkit.LoadEvent.FINISHED:
            if not self.text_select:
                webview.evaluate_javascript(
                    script=disable_text_select,
                    length=len(disable_text_select),
                    world_name=None,
                    source_uri=None,
                    cancellable=None,
                    callback=None)

            self._set_js_api()

    def on_download_started(self, session, download):
        download.connect('decide-destination', self.on_download_decide_destination)

    def on_download_decide_destination(self, download, suggested_filename):
        destination = self.create_file_dialog(
            SAVE_DIALOG,
            glib.get_user_special_dir(glib.UserDirectory.DIRECTORY_DOWNLOAD),
            False,
            suggested_filename,
            (),
        )

        if destination:
            destination_uri = glib.filename_to_uri(destination[0])
            download.set_destination(destination_uri)
        else:
            download.cancel()

    def on_navigation(self, webview, decision, decision_type):
        if type(decision) == webkit.NavigationPolicyDecision:
            uri = decision.get_navigation_action().get_request().get_uri()

            if decision.get_navigation_action().get_frame_name() == '_blank':
                if settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']:
                    webbrowser.open(uri, 2, True)
                    decision.ignore()
                else:
                    self.load_url(uri)
        elif type(decision) == webkit.ResponsePolicyDecision:
            if not decision.is_mime_type_supported():
                self._download_filename = decision.get_response().get_suggested_filename()
                decision.download()
            else:
                decision.use()

    def on_mouse_release(self, sender, event):
        self.move_progress = False

    def on_mouse_press(self, _, event):
        self.point_diff = [
            x - y for x, y in zip(self.window.get_position(), [event.x_root, event.y_root])
        ]
        self.move_progress = True

    def on_mouse_move(self, _, event):
        if self.move_progress:
            point = [x + y for x, y in zip((event.x_root, event.y_root), self.point_diff)]
            self.window.move(point[0], point[1])

    def show(self):
        self.window.show_all()

        if gtk.main_level() == 0:
            if self.pywebview_window.hidden:
                self.window.hide()
        else:
            glib.idle_add(self.window.show_all)

    def hide(self):
        glib.idle_add(self.window.hide)

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

    def resize(self, width, height, fix_point):
        if fix_point & FixPoint.NORTH and fix_point & FixPoint.WEST:
            self.window.set_gravity(Gdk.Gravity.NORTH_WEST)
        elif fix_point & FixPoint.NORTH and fix_point & FixPoint.EAST:
            self.window.set_gravity(Gdk.Gravity.NORTH_EAST)
        elif fix_point & FixPoint.SOUTH and fix_point & FixPoint.EAST:
            self.window.set_gravity(Gdk.Gravity.SOUTH_EAST)
        elif fix_point & FixPoint.SOUTH and fix_point & FixPoint.WEST:
            self.window.set_gravity(Gdk.Gravity.SOUTH_WEST)
        elif fix_point & FixPoint.SOUTH:
            self.window.set_gravity(Gdk.Gravity.SOUTH)
        elif fix_point & FixPoint.NORTH:
            self.window.set_gravity(Gdk.Gravity.NORTH)
        elif fix_point & FixPoint.WEST:
            self.window.set_gravity(Gdk.Gravity.WEST)
        elif fix_point & FixPoint.EAST:
            self.window.set_gravity(Gdk.Gravity.EAST)

        self.window.resize(width, height)

    def move(self, x, y):
        self.window.move(self.screen.x+x, self.screen.y+y)

    def maximize(self):
        glib.idle_add(self.window.maximize)

    def minimize(self):
        glib.idle_add(self.window.iconify)

    def restore(self):
        def _restore():
            self.window.deiconify()
            self.window.present()

        glib.idle_add(_restore)

    def create_confirmation_dialog(self, title, message):
        dialog = gtk.MessageDialog(
            parent=self.window,
            flags=gtk.DialogFlags.MODAL & gtk.DialogFlags.DESTROY_WITH_PARENT,
            type=gtk.MessageType.QUESTION,
            text=title,
            message_format=message,
            buttons=gtk.ButtonsType.OK_CANCEL,
        )
        response = dialog.run()
        dialog.destroy()
        if response == gtk.ResponseType.OK:
            return True

        return False

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_types):
        if dialog_type == FOLDER_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.SELECT_FOLDER
            title = self.localization['linux.openFolder']
            button = gtk.STOCK_OPEN
        elif dialog_type == OPEN_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.OPEN
            if allow_multiple:
                title = self.localization['linux.openFiles']
            else:
                title = self.localization['linux.openFile']

            button = gtk.STOCK_OPEN
        elif dialog_type == SAVE_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.SAVE
            title = self.localization['global.saveFile']
            button = gtk.STOCK_SAVE

        dialog = gtk.FileChooserDialog(
            title,
            self.window,
            gtk_dialog_type,
            (gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL, button, gtk.ResponseType.OK),
        )

        dialog.set_select_multiple(allow_multiple)
        dialog.set_current_folder(directory)
        self._add_file_filters(dialog, file_types)

        if dialog_type == SAVE_DIALOG:
            dialog.set_current_name(save_filename)

        response = dialog.run()

        if response == gtk.ResponseType.OK:
            if dialog_type == SAVE_DIALOG:
                file_name = (dialog.get_filename(),)
            else:
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

    def clear_cookies(self):
        def _clear_cookies():
            self.cookie_manager.delete_all_cookies()

        glib.idle_add(_clear_cookies)

    def get_cookies(self):
        def _get_cookies():
            self.cookie_manager.get_cookies(self.webview.get_uri(), None, callback, None)

        def callback(source, task, data):
            results = source.get_cookies_finish(task)

            for c in results:
                cookie = create_cookie(c.to_set_cookie_header())
                cookies.append(cookie)

            semaphore.release()

        self.loaded.wait()

        cookies = []
        semaphore = Semaphore(0)
        glib.idle_add(_get_cookies)
        semaphore.acquire()

        return cookies

    def get_current_url(self):
        self.loaded.wait()
        uri = self.webview.get_uri()
        return uri if uri != 'about:blank' else None

    def load_url(self, url):
        self.loaded.clear()
        self.webview.load_uri(url)

    def load_html(self, content, base_uri):
        self.loaded.clear()
        self.webview.load_html(content, base_uri)

    def evaluate_js(self, script):
        def _evaluate_js():
            self.webview.evaluate_javascript(
                    script=script,
                    length=len(script),
                    world_name=None,
                    source_uri=None,
                    cancellable=None,
                    callback=_callback)

        def _callback(webview, task):
            value = webview.evaluate_javascript_finish(task)
            result = value.to_string() if value else None

            if unique_id in self.js_results:
                self.js_results[unique_id]['result'] = result

            result_semaphore.release()

        unique_id = uuid1().hex
        result_semaphore = Semaphore(0)
        self.js_results[unique_id] = {'semaphore': result_semaphore, 'result': None}

        self.loaded.wait()
        glib.idle_add(_evaluate_js)
        result_semaphore.acquire()

        result = self.js_results[unique_id]['result']
        result = (
            None
            if result == 'undefined' or result == 'null' or result is None
            else result
            if result == ''
            else json.loads(result)
        )

        del self.js_results[unique_id]

        return result

    def _set_js_api(self):
        def create_bridge():
            script = inject_pywebview(self.js_bridge.window, 'gtk', uid=self.pywebview_window.uid)
            self.webview.evaluate_javascript(
                    script=script,
                    length=len(script),
                    world_name=None,
                    source_uri=None,
                    cancellable=None,
                    callback=None)

            self.loaded.set()

        glib.idle_add(create_bridge)


def setup_app():
    # MUST be called before create_window and set_app_menu
    global _app
    if _app is None:
        _app = gtk.Application.new(None, 0)


def create_window(window):
    global _app

    def create():
        browser = BrowserView(window)
        browser.show()

    def create_master_callback(app):
        create()

    if window.uid == 'master':
        main_thread().pydev_do_not_trace = True # vs code debugger hang fix
        _app.connect('activate', create_master_callback)
        _app.run()
        _app = None
    else:
        # _app will already have been activated by this point
        glib.idle_add(create)


def set_title(title, uid):
    def _set_title():
        i.set_title(title)

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_set_title)


def destroy_window(uid):
    def _destroy_window():
        i.close_window()

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_destroy_window)


def toggle_fullscreen(uid):
    def _toggle_fullscreen():
        i.toggle_fullscreen()

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_toggle_fullscreen)


def add_tls_cert(certfile):
    web_context = webkit.WebContext.get_default()
    cert = Gio.TlsCertificate.new_from_file(certfile)
    web_context.allow_tls_certificate_for_host(cert, '127.0.0.1')


def set_on_top(uid, top):
    def _set_on_top():
        i.window.set_keep_above(top)

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_set_on_top)


def resize(width, height, uid, fix_point):
    def _resize():
        i.resize(width, height, fix_point)

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_resize)


def move(x, y, uid):
    def _move():
        i.move(x, y)

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_move)


def hide(uid):
    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(i.hide)


def show(uid):
    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(i.show)


def maximize(uid):
    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(i.maximize)


def minimize(uid):
    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(i.minimize)


def restore(uid):
    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(i.restore)


def clear_cookies(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.clear_cookies()


def get_cookies(uid):
    i = BrowserView.instances.get(uid)
    if i:
        cookies = i.get_cookies()
        return cookies


def get_current_url(uid):
    def _get_current_url():
        result['url'] = i.get_current_url()
        semaphore.release()

    result = {}
    semaphore = Semaphore(0)

    i = BrowserView.instances.get(uid)
    if not i:
        return

    glib.idle_add(_get_current_url)
    semaphore.acquire()

    return result['url']


def load_url(url, uid):
    def _load_url():
        i.load_url(url)

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_load_url)


def load_html(content, base_uri, uid):
    def _load_html():
        i.load_html(content, base_uri)

    i = BrowserView.instances.get(uid)
    if i:
        glib.idle_add(_load_html)


def create_confirmation_dialog(title, message, uid):
    def _create():
        nonlocal result
        result = i.create_confirmation_dialog(title, message)
        result_semaphore.release()

    i = BrowserView.instances.get(uid)
    result_semaphore = Semaphore(0)
    result = -1

    if i:
        glib.idle_add(_create)
        result_semaphore.acquire()

    return result


def set_app_menu(app_menu_list):
    """
    Create a custom menu for the app bar menu (on supported platforms).
    Otherwise, this menu is used across individual windows.

    Args:
        app_menu_list ([webview.menu.Menu])
    """
    global _app_actions

    def action_callback(action, parameter):
        function = _app_actions.get(action.get_name())
        if function is None:
            return
        # Don't run action function on main thread
        Thread(target=function).start()

    def create_submenu(title, line_items, supermenu, action_prepend=''):
        m = Gio.Menu.new()
        current_section = Gio.Menu.new()
        action_prepend = '{}_{}'.format(action_prepend, title)
        for menu_line_item in line_items:
            if isinstance(menu_line_item, MenuSeparator):
                m.append_section(None, current_section)
                current_section = Gio.Menu.new()
            elif isinstance(menu_line_item, MenuAction):
                action_label = '{}_{}'.format(action_prepend, menu_line_item.title).replace(
                    ' ', '_'
                )
                while action_label in _app_actions.keys():
                    action_label += '_'
                _app_actions[action_label] = menu_line_item.function
                new_action = Gio.SimpleAction.new(action_label, None)
                new_action.connect('activate', action_callback)
                _app.add_action(new_action)
                current_section.append(menu_line_item.title, 'app.' + action_label)
            elif isinstance(menu_line_item, Menu):
                create_submenu(
                    menu_line_item.title,
                    menu_line_item.items,
                    current_section,
                    action_prepend=action_prepend,
                )

        m.append_section(None, current_section)

        supermenu.append_submenu(title, m)

    global _app

    menubar = Gio.Menu()

    for app_menu in app_menu_list:
        create_submenu(app_menu.title, app_menu.items, menubar)

    def set_menubar(app):
        app.set_menubar(menubar)

    _app.connect('startup', set_menubar)


def get_active_window():
    active_window = None
    try:
        active_window = _app.get_active_window()
    except:
        return None

    active_window_number = active_window.get_id()

    for uid, browser_view_instance in BrowserView.instances.items():
        if browser_view_instance.window.get_id() == active_window_number:
            return browser_view_instance.pywebview_window

    return None


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, uid):
    i = BrowserView.instances.get(uid)
    file_name_semaphore = Semaphore(0)
    file_names = []

    def _create():
        result = i.create_file_dialog(
            dialog_type, directory, allow_multiple, save_filename, file_types
        )
        if result is None:
            file_names.append(None)
        else:
            file_names.append(tuple(result))

        file_name_semaphore.release()

    glib.idle_add(_create)
    file_name_semaphore.acquire()

    return file_names[0]


def evaluate_js(script, uid):
    i = BrowserView.instances.get(uid)

    if i:
        return i.evaluate_js(script)


def get_position(uid):
    def _get_position():
        result['position'] = i.window.get_position()
        semaphore.release()

    i = BrowserView.instances.get(uid)
    if not i:
        return

    result = {}
    semaphore = Semaphore(0)

    glib.idle_add(_get_position)
    semaphore.acquire()

    return result['position']


def get_size(uid):
    def _get_size():
        result['size'] = i.window.get_size()
        semaphore.release()

    i = BrowserView.instances.get(uid)
    if not i:
        return

    result = {}
    semaphore = Semaphore(0)

    glib.idle_add(_get_size)
    semaphore.acquire()

    return result['size']


def get_screens():
    display = Gdk.Display.get_default()
    n = display.get_n_monitors()
    monitors = [Gdk.Display.get_monitor(display, i) for i in range(n)]
    geometries = [Gdk.Monitor.get_geometry(m) for m in monitors]
    screens = [Screen(geom.width, geom.height, geom) for geom in geometries]

    return screens


def configure_transparency(c):
    c.set_visual(c.get_screen().get_rgba_visual())
    c.override_background_color(gtk.StateFlags.ACTIVE, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.BACKDROP, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.DIR_LTR, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.DIR_RTL, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.FOCUSED, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.INCONSISTENT, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.INSENSITIVE, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.PRELIGHT, Gdk.RGBA(0, 0, 0, 0))
    c.override_background_color(gtk.StateFlags.SELECTED, Gdk.RGBA(0, 0, 0, 0))
    transparentWindowStyleProvider = gtk.CssProvider()
    transparentWindowStyleProvider.load_from_data(
        b"""
        GtkWindow {
            background-color:rgba(0,0,0,0);
            background-image:none;
        }"""
    )
    c.get_style_context().add_provider(
        transparentWindowStyleProvider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
