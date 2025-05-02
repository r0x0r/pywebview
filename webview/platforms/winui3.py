import atexit
import contextlib
import json
import logging
import os
import tempfile
import threading
import webbrowser
from concurrent.futures import Future, wait
from ctypes import WinError
from http.cookies import SimpleCookie
from threading import Event, Semaphore
from typing import Iterable, Optional, Sequence, Union, cast

from webview2.microsoft.web.webview2.core import (
    CoreWebView2,
    CoreWebView2Cookie,
    CoreWebView2CookieSameSiteKind,
    CoreWebView2DownloadStartingEventArgs,
    CoreWebView2Environment,
    CoreWebView2EnvironmentOptions,
    CoreWebView2File,
    CoreWebView2NavigationCompletedEventArgs,
    CoreWebView2NavigationStartingEventArgs,
    CoreWebView2NewWindowRequestedEventArgs,
    CoreWebView2ServerCertificateErrorAction,
    CoreWebView2ServerCertificateErrorDetectedEventArgs,
    CoreWebView2SourceChangedEventArgs,
    CoreWebView2WebMessageReceivedEventArgs,
)
from winrt.runtime import ApartmentType, init_apartment, uninit_apartment
from winrt.runtime.interop import initialize_with_window
from winrt.system import Array, Object, box_string
from winrt.windows.foundation import (
    AsyncStatus,
    IAsyncAction,
    IAsyncOperation,
    Uri,
)
from winrt.windows.storage import StorageFile, StorageFolder
from winrt.windows.storage.pickers import (
    FileOpenPicker,
    FileSavePicker,
    FolderPicker,
    PickerLocationId,
)
from winrt.windows.ui import Color, Colors
from winrt.windows.ui.xaml.interop import TypeKind, TypeName
from winui3.microsoft.ui import DisplayId
from winui3.microsoft.ui.interop import get_icon_id_from_icon, get_window_from_window_id
from winui3.microsoft.ui.windowing import (
    AppWindow,
    AppWindowChangedEventArgs,
    AppWindowClosingEventArgs,
    AppWindowPresenterKind,
    DisplayArea,
    DisplayAreaFallback,
    FullScreenPresenter,
    IconShowOptions,
    OverlappedPresenter,
    OverlappedPresenterState,
)
from winui3.microsoft.ui.xaml import (
    Application,
    ApplicationInitializationCallbackParams,
    LaunchActivatedEventArgs,
    UIElement,
    Visibility,
    Window,
    WindowActivatedEventArgs,
    WindowActivationState,
    WindowEventArgs,
    WindowSizeChangedEventArgs,
)
from winui3.microsoft.ui.xaml.controls import (
    ContentDialog,
    ContentDialogButton,
    ContentDialogResult,
    CoreWebView2InitializedEventArgs,
    Grid,
    MenuBar,
    MenuBarItem,
    MenuFlyoutItem,
    MenuFlyoutSeparator,
    MenuFlyoutSubItem,
    WebView2,
    XamlControlsResources,
)
from winui3.microsoft.ui.xaml.markup import (
    IXamlMetadataProvider,
    IXamlType,
    XamlReader,
    XmlnsDefinition,
)
from winui3.microsoft.ui.xaml.xamltypeinfo import XamlControlsXamlMetaDataProvider
from winui3.microsoft.windows.applicationmodel.dynamicdependency.bootstrap import (
    InitializeOptions,
    initialize,
)
from winui3.microsoft.windows.storage import ApplicationData

from webview import (
    FOLDER_DIALOG,
    OPEN_DIALOG,
    SAVE_DIALOG,
    _state,
    windows,
)
from webview import (
    settings as webview_settings,
)
from webview.dom import _dnd_state
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.platforms.win32 import (
    get_app_icon_handle,
    get_roaming_app_data_path,
    set_window_noactivate,
    show_save_file_dialog,
    win11_bootstrap,
)
from webview.screen import Screen
from webview.util import (
    DEFAULT_HTML,
    create_cookie,
    inject_pywebview,
    js_bridge_call,
    parse_file_type,
)
from webview.window import FixPoint
from webview.window import Window as _Window

logger = logging.getLogger("pywebview")
cache_dir: str | None = None
renderer = "winui3"


class EdgeChrome:
    def __init__(self, form: Window, window: _Window, cache_dir: str):
        self.pywebview_window = window
        self.webview = form.content.as_(Grid).find_name("webview").as_(WebView2)
        self.form = form

        self.js_result_semaphore = Semaphore(0)
        self.webview.add_core_webview2_initialized(self.on_webview_ready)
        self.webview.add_navigation_starting(self.on_navigation_start)
        self.webview.add_navigation_completed(self.on_navigation_completed)
        self.webview.add_web_message_received(self.on_script_notify)
        self.webview.default_background_color = Color(
            255,
            int(window.background_color.lstrip("#")[0:2], 16),
            int(window.background_color.lstrip("#")[2:4], 16),
            int(window.background_color.lstrip("#")[4:6], 16),
        )

        if window.transparent:
            self.webview.default_background_color = Colors.transparent

        self.url: str | None = None
        self.ishtml = False
        self.html: str = DEFAULT_HTML

        env_options = CoreWebView2EnvironmentOptions()
        env_options.additional_browser_arguments = (
            "--disable-features=ElasticOverscroll"
        )

        if webview_settings["ALLOW_FILE_URLS"]:
            env_options.additional_browser_arguments += (
                " --allow-file-access-from-files"
            )

        env_op = CoreWebView2Environment.create_with_options_async(
            "", cache_dir, env_options
        )

        def on_env_op_completed(
            op: IAsyncOperation[CoreWebView2Environment], status: AsyncStatus
        ):
            if status == AsyncStatus.ERROR:
                logger.error(
                    "Error creating CoreWebView2Environment: %r",
                    WinError(op.error_code.value),
                )
                return

            env = op.get_results()

            ctrl_options = env.create_core_webview2_controller_options()
            ctrl_options.is_in_private_mode_enabled = _state["private_mode"]

            ensure_op = (
                self.webview.ensure_core_webview2_with_environment_and_options_async(
                    env, ctrl_options
                )
            )

            def on_ensure_op_completed(op: IAsyncAction, status: AsyncStatus):
                if status == AsyncStatus.ERROR:
                    logger.error(
                        "Error creating CoreWebView2: %r", WinError(op.error_code.value)
                    )
                    return

                _main_window_created.set()

            ensure_op.completed = on_ensure_op_completed

        env_op.completed = on_env_op_completed

    def evaluate_js(self, script: str, parse_json: bool):
        result = None
        semaphore = Semaphore(0)

        def _callback(res: str | None):
            nonlocal result

            if parse_json and res is not None:
                try:
                    result = json.loads(res)
                except Exception:
                    result = res
            else:
                result = res

            semaphore.release()

        try:

            def callback():
                op = self.webview.execute_script_async(script)

                def on_completed(op: IAsyncOperation[str], status: AsyncStatus):
                    if status == AsyncStatus.ERROR:
                        logger.error(
                            "Error executing script: %r",
                            WinError(op.error_code.value),
                        )
                    elif status == AsyncStatus.COMPLETED:
                        _callback(json.loads(op.get_results()))

                op.completed = on_completed

            if not self.webview.dispatcher_queue.try_enqueue(callback):
                raise RuntimeError("Failed to enqueue dispatcher callback")

            semaphore.acquire()
        except Exception:
            logger.exception("Error occurred in script")
            semaphore.release()

        return result

    def clear_cookies(self):
        self.webview.core_webview2.cookie_manager.delete_all_cookies()

    def get_cookies(self, semaphore: Semaphore, cookies: list[SimpleCookie]):
        def _parse_cookies(_cookies: Sequence[CoreWebView2Cookie]):
            # cookies must be accessed in the main thread, otherwise an exception is thrown
            # https://github.com/MicrosoftEdge/WebView2Feedback/issues/1976
            for c in _cookies:
                same_site = (
                    None
                    if c.same_site == CoreWebView2CookieSameSiteKind.NONE
                    else c.same_site.name.lower()
                )
                try:
                    data = {
                        "name": c.name,
                        "value": c.value,
                        "path": c.path,
                        "domain": c.domain,
                        "expires": str(c.expires),
                        "secure": c.is_secure,
                        "httponly": c.is_http_only,
                        "samesite": same_site,
                    }

                    cookie = create_cookie(data)
                    cookies.append(cookie)
                except Exception as e:
                    logger.exception(e)

            semaphore.release()

        op = self.webview.core_webview2.cookie_manager.get_cookies_async(self.url or "")

        def on_op_completed(
            op: IAsyncOperation[Sequence[CoreWebView2Cookie]], status: AsyncStatus
        ):
            if status == AsyncStatus.ERROR:
                logger.error(
                    "Error getting cookies: %r",
                    WinError(op.error_code.value),
                )
                return
            elif status == AsyncStatus.COMPLETED:
                _cookies = op.get_results()

                def callback():
                    _parse_cookies(_cookies)

                if not self.webview.dispatcher_queue.try_enqueue(callback):
                    raise RuntimeError("Failed to enqueue dispatcher callback")

        op.completed = on_op_completed

    def get_current_url(self):
        return self.url

    def load_html(self, content: str, _: str):
        self.html = content
        self.ishtml = True

        if self.webview.core_webview2:
            self.webview.core_webview2.navigate_to_string(self.html)
        else:
            self.webview.ensure_core_webview2_async()

    def load_url(self, url: str):
        self.ishtml = False
        self.webview.source = Uri(url)

    def on_certificate_error(
        self, _: CoreWebView2, args: CoreWebView2ServerCertificateErrorDetectedEventArgs
    ):
        args.action = CoreWebView2ServerCertificateErrorAction.ALWAYS_ALLOW

    def on_script_notify(
        self, sender: WebView2, args: CoreWebView2WebMessageReceivedEventArgs
    ):
        try:
            return_value = args.web_message_as_json

            if return_value == '"FilesDropped"':
                if _dnd_state["num_listeners"] == 0:
                    return
                additional_objects = args.additional_objects
                if not additional_objects:
                    return

                files = [
                    (os.path.basename(file.path), file.path)
                    for file in [
                        obj.as_(CoreWebView2File)
                        for obj in additional_objects
                        if obj._runtime_class_name_ == "CoreWebView2File"
                    ]
                ]
                _dnd_state["paths"] += files
                return

            func_name, func_param, value_id = json.loads(return_value)
            func_param = json.loads(func_param)

            if func_name == "_pywebviewAlert":
                dialog = ContentDialog()
                dialog.xaml_root = self.webview.xaml_root
                dialog.content = box_string(str(func_param))
                dialog.close_button_text = self.pywebview_window.localization[
                    "global.ok"
                ]
                dialog.default_button = ContentDialogButton.CLOSE

                op = dialog.show_async()

                def on_completed(
                    op: IAsyncOperation[ContentDialogResult], status: AsyncStatus
                ):
                    if status == AsyncStatus.ERROR:
                        logger.error(
                            "Error showing ContentDialog: %r",
                            WinError(op.error_code.value),
                        )
                        return

                    # nothing to do here, but we have to have a completed
                    # callback to make things work properly
                    if status == AsyncStatus.COMPLETED:
                        op.get_results()

                op.completed = on_completed
            elif func_name == "console":
                print(func_param)
            else:
                js_bridge_call(self.pywebview_window, func_name, func_param, value_id)
        except Exception:
            logger.exception("Exception occurred during on_script_notify")

    def on_new_window_request(
        self, sender: CoreWebView2, args: CoreWebView2NewWindowRequestedEventArgs
    ):
        args.handled = True

        if webview_settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"]:
            webbrowser.open(args.uri)
        else:
            self.load_url(args.uri)

    def on_source_changed(
        self, sender: CoreWebView2, args: CoreWebView2SourceChangedEventArgs
    ):
        self.url = sender.source or None
        self.ishtml = False

    def on_webview_ready(
        self, sender: WebView2, args: CoreWebView2InitializedEventArgs
    ):
        if args.exception.value:
            logger.error(
                "WebView2 initialization failed with exception:\n%s",
                WinError(args.exception.value).strerror,
            )
            return

        sender.core_webview2.add_source_changed(self.on_source_changed)
        sender.core_webview2.add_new_window_requested(self.on_new_window_request)

        if _state["ssl"]:
            sender.core_webview2.add_server_certificate_error_detected(
                self.on_certificate_error
            )

        sender.core_webview2.add_download_starting(self.on_download_starting)

        settings = sender.core_webview2.settings
        settings.are_browser_accelerator_keys_enabled = _state["debug"]
        settings.are_default_context_menus_enabled = _state["debug"]
        settings.are_default_script_dialogs_enabled = True
        settings.are_dev_tools_enabled = _state["debug"]
        settings.is_built_in_error_page_enabled = True
        settings.is_script_enabled = True
        settings.is_web_message_enabled = True
        settings.is_status_bar_enabled = _state["debug"]
        settings.is_swipe_navigation_enabled = False
        settings.is_zoom_control_enabled = True

        if _state["user_agent"]:
            settings.user_agent = _state["user_agent"]

        if _state["private_mode"]:
            # cookies persist even if UserDataFolder is in memory. We have to delete cookies manually.
            sender.core_webview2.cookie_manager.delete_all_cookies()

        if self.pywebview_window.real_url:
            self.load_url(self.pywebview_window.real_url)
        elif self.pywebview_window.html:
            self.html = self.pywebview_window.html
            self.load_html(self.pywebview_window.html, "")
        else:
            self.load_html(DEFAULT_HTML, "")

        if _state["debug"] and webview_settings["OPEN_DEVTOOLS_IN_DEBUG"]:
            sender.core_webview2.open_dev_tools_window()

    def on_download_starting(
        self, sender: CoreWebView2, args: CoreWebView2DownloadStartingEventArgs
    ):
        args.cancel = True

        if not webview_settings["ALLOW_DOWNLOADS"]:
            return

        path = show_save_file_dialog(
            self.form.app_window.id.value,
            os.path.basename(args.result_file_path),
            self.pywebview_window.localization["windows.fileFilter.allFiles"],
            "*.*",
        )
        if path is None:
            return

        args.result_file_path = path
        args.cancel = False

    def on_navigation_start(
        self, sender: WebView2, args: CoreWebView2NavigationStartingEventArgs
    ):
        pass

    def on_navigation_completed(
        self, sender: WebView2, _: CoreWebView2NavigationCompletedEventArgs
    ):
        url = str(sender.source)
        self.url = None if self.ishtml else url

        inject_pywebview(renderer, self.pywebview_window)


_WINDOW_XAML = """
<Grid xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">
    <Grid.RowDefinitions>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="*"/>
    </Grid.RowDefinitions>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="Auto"/>
    </Grid.ColumnDefinitions>

    <MenuBar Name="menu" Grid.Row="0" Grid.ColumnSpan="2" Visibility="collapsed"/>
    <WebView2 Name="webview" Grid.Row="1" Grid.ColumnSpan="2"
        HorizontalAlignment="Stretch" VerticalAlignment="Stretch"/>
</Grid>
"""

class PyWebviewWindow(Window):
    # Have to subclass Window just to add webview attribute so that
    # window.native.webview works.
    webview: WebView2

class BrowserView:
    instances: dict[str, "BrowserForm"] = {}

    app_menu_list: Iterable[Menu] = []

    class BrowserForm:
        def __init__(self, window: _Window, cache_dir: str):
            self._is_active = False
            self.uid = window.uid
            self.pywebview_window = window
            self.window = PyWebviewWindow()
            self.handle = get_window_from_window_id(self.window.app_window.id)
            self.real_url = None

            self.pywebview_window.native = self.window

            self.window.title = window.title
            self.window.content = XamlReader.load(_WINDOW_XAML).as_(UIElement)
            self.window.app_window.resize((window.initial_width, window.initial_height))

            # TODO: No APIs yet for minimum size
            # https://github.com/microsoft/microsoft-ui-xaml/issues/7296
            # self.MinimumSize = Size(window.min_size[0], window.min_size[1])

            if window.initial_x is not None and window.initial_y is not None:
                self.window.app_window.move((window.initial_x, window.initial_y))
            elif window.screen:
                did = cast(DisplayId, window.screen.frame)
                area = DisplayArea.get_from_display_id(did)
                x = (area.work_area.width - self.window.app_window.size.width) // 2
                y = (area.work_area.height - self.window.app_window.size.height) // 2
                self.window.app_window.move((x, y))
            else:
                area = DisplayArea.get_from_window_id(
                    self.window.app_window.id, DisplayAreaFallback.NEAREST
                )
                x = (area.work_area.width - self.window.app_window.size.width) // 2
                y = (area.work_area.height - self.window.app_window.size.height) // 2
                self.window.app_window.move((x, y))

            self.full_screen_presenter = FullScreenPresenter.create()
            self.overlapped_presenter = self.window.app_window.presenter.as_(
                OverlappedPresenter
            )
            self.overlapped_presenter.is_resizable = window.resizable
            self.old_state = self.overlapped_presenter.state

            # apply windows theme to title bar
            self.window.app_window.title_bar.icon_show_options = (
                IconShowOptions.SHOW_ICON_AND_SYSTEM_MENU
            )

            icon_handle = get_app_icon_handle()
            icon_id = get_icon_id_from_icon(icon_handle)
            self.window.app_window.set_icon_with_icon_id(icon_id)
            # app_window doesn't take a reference, so don't call DestroyIcon(icon_handle)!

            self.url = window.real_url

            # self.TopMost = window.on_top

            if window.fullscreen:
                self.toggle_fullscreen()

            if window.frameless:
                self.overlapped_presenter.set_border_and_title_bar(False, False)

            if BrowserView.app_menu_list:
                self.set_window_menu(BrowserView.app_menu_list)

            self.browser = EdgeChrome(self.window, window, cache_dir)
            self.webview = self.browser.webview
            # Part of the public API, so we have to set it.
            self.pywebview_window.native.webview = self.webview

            # if (
            #     window.transparent and self.browser
            # ):  # window transparency is supported only with EdgeChromium
            #     self.BackColor = Color.FromArgb(255,255,0,0)
            #     self.TransparencyKey = Color.FromArgb(255,255,0,0)
            #     self.SetStyle(WinForms.ControlStyles.SupportsTransparentBackColor, True)
            #     self.browser.DefaultBackgroundColor = Color.Transparent
            # else:
            #     self.BackColor = ColorTranslator.FromHtml(window.background_color)

            if not window.focus:
                set_window_noactivate(self.handle)

            self.window.add_activated(self.on_activated)
            self.window.add_closed(self.on_close)
            self.window.app_window.add_closing(self.on_closing)
            self.window.add_size_changed(self.on_resize)
            self.window.app_window.add_changed(self.on_changed)

            self.localization = window.localization

        def __str__(self):
            return f"<Window object with {self.handle} handle>"

        def on_activated(self, sender: Object, args: WindowActivatedEventArgs):
            self._is_active = (
                args.window_activation_state != WindowActivationState.DEACTIVATED
            )
            self.pywebview_window.events.shown.set()

            if not self._is_active:
                return

            if not self.pywebview_window.focus:
                set_window_noactivate(self.handle)

        def on_close(self, sender: Object, args: WindowEventArgs):
            # stop waiting for JS result
            self.browser.js_result_semaphore.release()

            del BrowserView.instances[self.uid]

            # during tests windows is empty for some reason. no idea why.
            if self.pywebview_window in windows:
                windows.remove(self.pywebview_window)

            self.pywebview_window.events.closed.set()

            if len(BrowserView.instances) == 0:
                Application.current.exit()

        def on_closing(self, sender: AppWindow, args: AppWindowClosingEventArgs):
            should_cancel = self.pywebview_window.events.closing.set()

            if should_cancel:
                args.cancel = True

            if args.cancel:
                return

            if self.pywebview_window.confirm_close:
                # WinUI 3 doesn't have a way to disable the window close button
                # so we have to make it do nothing until the dialog is closed
                def disable_close():
                    return False

                self.pywebview_window.events.closing += disable_close
                dialog = self.create_confirmation_dialog(
                    self.window.title, self.localization["global.quitConfirmation"]
                )
                op = dialog.show_async()

                def on_completed(
                    op: IAsyncOperation[ContentDialogResult], status: AsyncStatus
                ):
                    self.pywebview_window.events.closing -= disable_close

                    if status == AsyncStatus.ERROR:
                        logger.error(
                            "Error showing ContentDialog: %r",
                            WinError(op.error_code.value),
                        )
                        return

                    if status == AsyncStatus.COMPLETED:
                        result = op.get_results()

                        if result == ContentDialogResult.PRIMARY:
                            self.window.close()

                op.completed = on_completed

                # have to cancel closing so the dialog can be shown
                args.cancel = True

        def on_resize(self, sender: Object, args: WindowSizeChangedEventArgs):
            self.pywebview_window.events.resized.set(args.size.width, args.size.height)

        def on_changed(self, sender: AppWindow, args: AppWindowChangedEventArgs):
            if self.overlapped_presenter.state != self.old_state:
                if (
                    self.overlapped_presenter.state
                    == OverlappedPresenterState.MAXIMIZED
                ):
                    self.pywebview_window.events.maximized.set()
                elif (
                    self.overlapped_presenter.state
                    == OverlappedPresenterState.MINIMIZED
                ):
                    self.pywebview_window.events.minimized.set()
                elif (
                    self.overlapped_presenter.state == OverlappedPresenterState.RESTORED
                ):
                    self.pywebview_window.events.restored.set()

                self.old_state = self.overlapped_presenter.state
            elif args.did_position_change:
                x, y = self.window.app_window.position.unpack()
                self.pywebview_window.events.moved.set(x, y)

        def evaluate_js(self, script: str, parse_json: bool):
            result = self.browser.evaluate_js(script, parse_json)
            return result

        def create_confirmation_dialog(self, title: str, message: str) -> ContentDialog:
            dialog = ContentDialog()
            dialog.xaml_root = self.window.content.xaml_root
            dialog.title = box_string(title)
            dialog.content = box_string(message)
            dialog.primary_button_text = self.localization["global.ok"]
            dialog.close_button_text = self.localization["global.cancel"]
            dialog.default_button = ContentDialogButton.PRIMARY

            return dialog

        @staticmethod
        def invoke_on_ui_thread(func):
            def wrapper(self: "BrowserView.BrowserForm", *args, **kwargs):
                if self.window.dispatcher_queue.has_thread_access:
                    return func(self, *args, **kwargs)

                event = Event()
                result = None

                def invoke():
                    nonlocal result

                    try:
                        result = func(self, *args, **kwargs)
                    finally:
                        event.set()

                if not self.window.dispatcher_queue.try_enqueue(invoke):
                    raise RuntimeError("Failed to enqueue dispatcher callback")

                event.wait()

                return result

            return wrapper

        @invoke_on_ui_thread
        def set_title(self, title: str):
            self.window.title = title

        @invoke_on_ui_thread
        def clear_cookies(self):
            self.browser.clear_cookies()

        @invoke_on_ui_thread
        def get_cookies(self, semaphore: Semaphore, cookies: list[SimpleCookie]):
            self.browser.get_cookies(semaphore, cookies)

        @invoke_on_ui_thread
        def load_html(self, content: str, base_uri: str):
            self.browser.load_html(content, base_uri)

        @invoke_on_ui_thread
        def load_url(self, url: str):
            self.browser.load_url(url)

        @invoke_on_ui_thread
        def hide(self):
            self.window.app_window.hide()

        @invoke_on_ui_thread
        def show(self):
            self.window.app_window.show()
            self.window.activate()

        def is_active(self) -> bool:
            return self._is_active

        @invoke_on_ui_thread
        def set_window_menu(self, menu_list: Iterable[Menu]):
            def create_action_item(action: MenuAction) -> MenuFlyoutItem:
                action_item = MenuFlyoutItem()
                action_item.text = action.title

                # Don't run action function on main thread
                action_item.add_click(
                    lambda s, e: threading.Thread(target=action.function).start()
                )

                return action_item

            def create_submenu(
                title: str,
                line_items: Iterable[Union[Menu, MenuAction, MenuSeparator]],
                supermenu: Optional[MenuFlyoutSubItem] = None,
            ) -> MenuFlyoutSubItem:
                m = MenuFlyoutSubItem()
                m.text = title

                for menu_line_item in line_items:
                    if isinstance(menu_line_item, MenuSeparator):
                        m.items.append(MenuFlyoutSeparator())
                        continue
                    elif isinstance(menu_line_item, MenuAction):
                        m.items.append(create_action_item(menu_line_item))
                    elif isinstance(menu_line_item, Menu):
                        create_submenu(menu_line_item.title, menu_line_item.items, m)

                if supermenu:
                    supermenu.items.append(m)

                return m

            def create_menu_item(menu: Menu) -> MenuBarItem:
                m = MenuBarItem()
                m.title = menu.title

                for menu_item in menu.items:
                    if isinstance(menu_item, MenuAction):
                        item = create_action_item(menu_item)
                    elif isinstance(menu_item, Menu):
                        item = create_submenu(menu_item.title, menu_item.items)
                    elif isinstance(menu_item, MenuSeparator):
                        item = MenuFlyoutSeparator()

                    m.items.append(item)

                return m

            top_level_menu = (
                self.window.content.as_(Grid).find_name("menu").as_(MenuBar)
            )
            top_level_menu.visibility = Visibility.VISIBLE

            for menu in menu_list:
                top_level_menu.items.append(create_menu_item(menu))

        @invoke_on_ui_thread
        def toggle_fullscreen(self):
            if (
                self.window.app_window.presenter.kind
                == AppWindowPresenterKind.FULL_SCREEN
            ):
                self.window.app_window.set_presenter(self.overlapped_presenter)
            else:
                self.window.app_window.set_presenter(self.full_screen_presenter)

        @invoke_on_ui_thread
        def set_on_top(self, on_top: bool):
            self.overlapped_presenter.is_always_on_top = on_top

        @invoke_on_ui_thread
        def get_size(self):
            return self.window.app_window.size.unpack()

        @invoke_on_ui_thread
        def resize(self, width: int, height: int, fix_point: FixPoint):
            x, y = self.window.app_window.position.unpack()

            if fix_point & FixPoint.EAST:
                x += self.window.app_window.size.width - width

            if fix_point & FixPoint.SOUTH:
                y += self.window.app_window.size.height - height

            self.window.app_window.move_and_resize((x, y, width, height))

        @invoke_on_ui_thread
        def get_position(self):
            return self.window.app_window.position.unpack()

        @invoke_on_ui_thread
        def move(self, x: int, y: int):
            self.window.app_window.move((x, y))

        @invoke_on_ui_thread
        def maximize(self):
            self.overlapped_presenter.maximize()

        @invoke_on_ui_thread
        def minimize(self):
            self.overlapped_presenter.minimize()

        @invoke_on_ui_thread
        def restore(self):
            self.overlapped_presenter.restore()

        @invoke_on_ui_thread
        def close(self):
            self.window.close()


_main_window_created = Event()
_app_exit_stack = contextlib.ExitStack()


def init_storage():
    global cache_dir

    if not _state["private_mode"] or _state["storage_path"]:
        try:
            try:
                # Only succeeds if the current process has package identity.
                app_data = ApplicationData.get_default()
                data_folder = app_data.shared_local_path
            except OSError as ex:
                if ex.winerror != -2147009196:  # The process has no package identity.
                    raise

                data_folder = get_roaming_app_data_path()

            cache_dir = _state["storage_path"] or os.path.join(data_folder, "pywebview")

            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
        except Exception:
            logger.exception(f"Cache directory {cache_dir} creation failed")
    else:
        _cache_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        atexit.register(_cache_dir.cleanup)
        cache_dir = _cache_dir.name


_app_setup = False


def setup_app():
    # MUST be called before create_window and set_app_menu
    global _app_setup

    if _app_setup:
        return

    init_apartment(ApartmentType.SINGLE_THREADED)
    _app_exit_stack.callback(uninit_apartment)

    try:
        _app_exit_stack.enter_context(
            initialize(options=InitializeOptions.ON_NO_MATCH_SHOW_UI)
        )
    except OSError as e:
        ERROR_NOT_SUPPORTED = -2147024846

        # If the Python runtime is from the Microsoft Store, the Windows App
        # SDK bootstrap will fail with this error because the Python runtime
        # is a packaged app.
        if e.winerror != ERROR_NOT_SUPPORTED:
            raise

        # TODO: If Windows version is less than 11, show a message box to the
        # user that explains to use a different Python runtime not from the
        # Microsoft store.

        # We can work around this, but only on Windows 11.
        win11_bootstrap()

    _app_setup = True


def create_window(window: _Window):
    def create() -> None:
        browser = BrowserView.BrowserForm(window, cache_dir)
        BrowserView.instances[window.uid] = browser
        window.events.before_show.set()

        if window.hidden:
            browser.overlapped_presenter.minimize_with_activation(True)
            browser.window.app_window.hide()
        else:
            browser.window.activate()

            if window.maximized:
                browser.overlapped_presenter.maximize()
            elif window.minimized:
                browser.overlapped_presenter.minimize()

    if window.uid == "master":
        init_storage()

        def init_app(_: ApplicationInitializationCallbackParams):
            class App(Application, IXamlMetadataProvider):
                def __init__(self) -> None:
                    self._provider = XamlControlsXamlMetaDataProvider()

                def _on_launched(self, args: LaunchActivatedEventArgs) -> None:
                    # Have to add some default resources here, otherwise the
                    # app will crash when trying to create menus
                    resources = XamlControlsResources()
                    self.resources.merged_dictionaries.append(resources)

                    create()

                def get_xaml_type(
                    self, type: TypeName | tuple[str, TypeKind]
                ) -> IXamlType:
                    return self._provider.get_xaml_type(type)

                def get_xaml_type_by_full_name(self, full_name: str) -> IXamlType:
                    return self._provider.get_xaml_type_by_full_name(full_name)

                def get_xmlns_definitions(self) -> Array[XmlnsDefinition]:
                    return self._provider.get_xmlns_definitions()

            App()

        Application.start(init_app)
        _app_exit_stack.close()
    else:
        _main_window_created.wait()
        i = list(BrowserView.instances.values())[0]  # arbitrary instance

        if not i.window.dispatcher_queue.try_enqueue(create):
            raise RuntimeError("Failed to enqueue callback")


def set_title(title: str, uid: str):
    i = BrowserView.instances.get(uid)

    if i:
        i.set_title(title)


def create_confirmation_dialog(title: str, message: str, uid: str) -> bool | None:
    i = BrowserView.instances.get(uid)
    if not i:
        return None

    # REVISIT: It doesn't seem like we should be waiting here but rather block
    # the window creation function until the main window is actually ready
    _main_window_created.wait()

    fut = Future[bool]()

    def callback():
        dialog = i.create_confirmation_dialog(title, message)

        op = dialog.show_async()

        def on_completed(op: IAsyncOperation[ContentDialogResult], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                fut.set_exception(WinError(op.error_code.value))
            elif status == AsyncStatus.CANCELED:
                fut.cancel()
            elif status == AsyncStatus.COMPLETED:
                result = op.get_results()
                fut.set_result(result == ContentDialogResult.PRIMARY)

        op.completed = on_completed

    if not i.window.dispatcher_queue.try_enqueue(callback):
        raise RuntimeError("Failed to enqueue callback")

    wait([fut])

    return fut.result()


def create_file_dialog(
    dialog_type: int,
    directory: str,
    allow_multiple: bool,
    save_filename: str,
    file_types: list[str],
    uid: str,
) -> str | tuple[str] | None:
    i = BrowserView.instances.get(uid)
    if not i:
        return None

    if not directory:
        directory = os.environ["HOMEPATH"]

    # FIXME: These Windows App SDK doesn't allow setting the starting location
    # https://github.com/microsoft/WindowsAppSDK/issues/88
    # Likely, we will need to replace these with win32 calls
    # https://learn.microsoft.com/en-us/uwp/api/windows.storage.pickers.filesavepicker?view=winrt-26100#in-a-desktop-app-that-requires-elevation

    fut = Future[str | tuple[str] | None]()

    if dialog_type == FOLDER_DIALOG:

        def callback():
            picker = FolderPicker()
            initialize_with_window(picker, i.handle)
            picker.suggested_start_location = PickerLocationId.DOWNLOADS

            # FIXME: This doesn't work with the Windows App SDK
            if allow_multiple:
                raise NotImplementedError("Multiple folders not supported")

            op = picker.pick_single_folder_async()

            def on_completed(op: IAsyncOperation[StorageFolder], status: AsyncStatus):
                if status == AsyncStatus.ERROR:
                    fut.set_exception(WinError(op.error_code.value))
                elif status == AsyncStatus.CANCELED:
                    fut.cancel()
                elif status == AsyncStatus.COMPLETED:
                    result = op.get_results()
                    fut.set_result(result.path)

            op.completed = on_completed

    elif dialog_type == OPEN_DIALOG:

        def callback():
            picker = FileOpenPicker()
            initialize_with_window(picker, i.handle)
            picker.suggested_start_location = PickerLocationId.DOWNLOADS

            if len(file_types) > 0:
                picker.file_type_filter.append("*")
            else:
                picker.file_type_filter.append("*")

            if allow_multiple:
                op = picker.pick_multiple_files_async()

                def on_completed1(
                    op: IAsyncOperation[Sequence[StorageFile]], status: AsyncStatus
                ):
                    if status == AsyncStatus.ERROR:
                        fut.set_exception(WinError(op.error_code.value))
                    elif status == AsyncStatus.CANCELED:
                        fut.cancel()
                    elif status == AsyncStatus.COMPLETED:
                        result = op.get_results()
                        fut.set_result([f.path for f in result])

                op.completed = on_completed1
            else:
                op = picker.pick_single_file_async()

                def on_completed2(
                    op: IAsyncOperation[StorageFile], status: AsyncStatus
                ):
                    if status == AsyncStatus.ERROR:
                        fut.set_exception(WinError(op.error_code.value))
                    elif status == AsyncStatus.CANCELED:
                        fut.cancel()
                    elif status == AsyncStatus.COMPLETED:
                        result = op.get_results()
                        fut.set_result(result.path)

                op.completed = on_completed2

    elif dialog_type == SAVE_DIALOG:

        def callback():
            picker = FileSavePicker()
            initialize_with_window(picker, i.handle)
            picker.suggested_start_location = PickerLocationId.DOWNLOADS
            picker.settings_identifier = uid
            picker.suggested_file_name = save_filename

            if len(file_types) > 0:
                picker.file_type_choices.update(
                    {k: [v[1:]] for k, v in [parse_file_type(f) for f in file_types]}
                )
            else:
                # winui3 doesn't allow wildcard file types in save dialog
                picker.file_type_choices[""] = ["."]

            op = picker.pick_save_file_async()

            def on_completed(op: IAsyncOperation[StorageFile], status: AsyncStatus):
                if status == AsyncStatus.ERROR:
                    fut.set_exception(WinError(op.error_code.value))
                elif status == AsyncStatus.CANCELED:
                    fut.cancel()
                elif status == AsyncStatus.COMPLETED:
                    result = op.get_results()

                    if not result:
                        fut.set_result(None)
                        return

                    fut.set_result(result.path)

            op.completed = on_completed

    else:
        raise ValueError("Invalid dialog type")

    if not i.window.dispatcher_queue.try_enqueue(callback):
        raise RuntimeError("Failed to enqueue callback")

    wait([fut])

    return fut.result()


def clear_cookies(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.clear_cookies()


def get_cookies(uid: str):
    i = BrowserView.instances.get(uid)
    if not i:
        return

    semaphore = Semaphore(0)
    cookies: list[SimpleCookie] = []

    i.get_cookies(semaphore, cookies)

    semaphore.acquire()

    return cookies


def get_current_url(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        return i.browser.url


def load_url(url: str, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.load_url(url)


def load_html(content: str, base_uri: str, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.load_html(content, base_uri)


def set_app_menu(app_menu_list: Iterable[Menu]):
    BrowserView.app_menu_list = app_menu_list


def get_active_window():
    for i in BrowserView.instances.values():
        if i.is_active():
            return i.pywebview_window

    return None


def show(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.show()


def hide(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.hide()


def toggle_fullscreen(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.toggle_fullscreen()


def set_on_top(uid: str, on_top: bool):
    i = BrowserView.instances.get(uid)
    if i:
        i.set_on_top(on_top)


def resize(width: int, height: int, uid: str, fix_point: FixPoint):
    i = BrowserView.instances.get(uid)
    if i:
        i.resize(width, height, fix_point)


def move(x: int, y: int, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.move(x, y)


def maximize(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.maximize()


def minimize(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.minimize()


def restore(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.restore()


def destroy_window(uid: str):
    i = BrowserView.instances.get(uid)
    if not i:
        return

    i.close()
    i.browser.js_result_semaphore.release()


def evaluate_js(script: str, uid: str, parse_json: bool = True):
    i = BrowserView.instances.get(uid)
    if i:
        return i.evaluate_js(script, parse_json)


def get_position(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        return i.get_position()


def get_size(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        return i.get_size()


def get_screens():
    # Can't directly iterate return value of find_all(). Workaround is to
    # get by index. https://github.com/microsoft/microsoft-ui-xaml/issues/6454
    all_displays = DisplayArea.find_all()

    return [
        Screen(
            da.outer_bounds.x,
            da.outer_bounds.y,
            da.outer_bounds.width,
            da.outer_bounds.height,
            da.display_id,
        )
        for da in (all_displays[i] for i in range(len(all_displays)))
    ]


def add_tls_cert(_):
    return
