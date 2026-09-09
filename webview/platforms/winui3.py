import atexit
import contextlib
import json
import logging
import os
import struct
import tempfile
import threading
from collections.abc import Iterable, Sequence
from concurrent.futures import Future, wait
from ctypes import WinError, windll
from datetime import datetime, timezone
from email.utils import format_datetime
from http.cookies import SimpleCookie
from threading import Event, Lock, Semaphore
from typing import cast

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
    CoreWebView2WebResourceContext,
    CoreWebView2WebResourceRequestedEventArgs,
    CoreWebView2WebResourceResponseReceivedEventArgs,
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
from winrt.windows.ui import Color
from winrt.windows.ui.xaml.interop import TypeKind, TypeName
from winui3.microsoft.ui import DisplayId
from winui3.microsoft.ui.interop import get_window_from_window_id
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
    FileDialog,
    _state,
    windows,
)
from webview import (
    settings as webview_settings,
)
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.platforms.webview2core import WebView2Core
from webview.platforms.win32 import (
    GWL_EXSTYLE,
    WS_EX_APPWINDOW,
    WS_EX_TOOLWINDOW,
    enable_window_shadow,
    get_monitor_scale,
    install_mouse_hook,
    pick_files_win32,
    pick_folders_win32,
    pick_save_file_win32,
    uninstall_mouse_hook,
)
from webview.screen import Screen
from webview.util import (
    create_cookie,
    get_app_root,
    inject_base_uri,
    inject_pywebview,
    parse_file_type,
)
from webview.window import FixPoint
from webview.window import Window as _Window

logger = logging.getLogger('pywebview')
cache_dir: str | None = None
renderer = 'winui3'

logger.debug('Using WinUI 3 / Chromium')


def _enqueue(dispatcher_queue, callback) -> bool:
    """Enqueue ``callback`` on the UI thread, logging on failure.

    Returns True on success, False if the queue rejected the callback (e.g. the
    UI thread is shutting down). Callers should treat False as a terminal
    condition and release any waiters they own.
    """
    if dispatcher_queue.try_enqueue(callback):
        return True
    logger.error('Failed to enqueue dispatcher callback')
    return False


def _guard_future_callback(callback, future: Future):
    """Transfer synchronous dispatcher callback failures to its waiting future."""

    def guarded_callback():
        try:
            callback()
        except BaseException as ex:
            if not future.done():
                future.set_exception(ex)

    return guarded_callback


def _run_dispatched(
    dispatcher_queue, callback, future: Future, may_complete_synchronously: bool = False
):
    """
    Run ``callback`` (which must eventually resolve ``future``) on the UI
    thread and return its result.

    If the calling thread already has dispatcher access — e.g. a native XAML
    event handler calling back into this module — enqueueing and then
    blocking this same thread on ``future`` would deadlock: nothing else can
    pump the queue to run the enqueued callback.

    ``may_complete_synchronously`` must be True only when ``callback`` is
    known, for this specific call, to resolve ``future`` before returning
    (e.g. a Win32 IFileDialog fallback pumping its own modal loop via
    Show()) — in that case it's run inline and its real result returned.
    When False (the default — a genuinely async operation like
    ContentDialog.show_async() or a WinRT picker's *_async(), which only
    resolve ``future`` later from a ``.completed`` callback), raise
    *before* invoking ``callback`` at all: starting it and then raising
    would leave a dialog visibly on screen (or a script running) with no
    way for the caller — who already received an exception — to ever see
    its result. Silently returning ``None`` instead of raising would also
    violate the caller's documented contract (a ``bool``, a path —
    indistinguishable from user cancellation, a synchronous script
    result, ...).

    If enqueueing fails (e.g. the UI thread is shutting down), returns
    ``None`` — ``future`` will never resolve, but this is an existing,
    narrower failure mode than the thread-reentrancy case above.

    Otherwise (the common case — called from a background thread), enqueue
    normally, block until ``future`` resolves, and return its result (or
    re-raise its exception).
    """
    if dispatcher_queue.has_thread_access:
        if not may_complete_synchronously:
            raise RuntimeError(
                'This operation cannot be started synchronously from a native '
                'UI-thread callback (e.g. a XAML event handler): it only '
                'resolves later, asynchronously, and this thread has no safe '
                'way to wait for that without deadlocking the dispatcher.'
            )
        guarded = _guard_future_callback(callback, future)
        guarded()
        if future.done():
            return future.result()
        raise RuntimeError(
            'This operation was started, but its result cannot be awaited '
            'synchronously from a native UI-thread callback (e.g. a XAML '
            'event handler) without deadlocking the dispatcher that must '
            'deliver it.'
        )

    guarded = _guard_future_callback(callback, future)
    if not _enqueue(dispatcher_queue, guarded):
        return None

    wait([future])
    return future.result()


def _format_cookie_expiry(expires: float, is_session: bool) -> str | None:
    """
    Convert CoreWebView2Cookie.expires (seconds since the Unix epoch) to the
    HTTP-date format (e.g. 'Wed, 21 Oct 2026 07:28:00 GMT') the cookie's
    Expires attribute requires. WinRT projects this property as a raw
    double, unlike the WinForms/.NET binding, which exposes an
    already-formattable DateTime.

    A session cookie is identified via CoreWebView2Cookie.is_session, the
    documented authoritative flag — not by treating a negative `expires` as
    a sentinel, since only `is_session` is guaranteed to mean "no expiry".
    """
    if is_session or expires is None:
        return None
    return format_datetime(datetime.fromtimestamp(expires, tz=timezone.utc), usegmt=True)


def _primary_monitor_scale() -> float:
    """
    DPI scale of the primary monitor — the single shared reference scale
    ``get_screens()`` uses to convert every monitor's physical-pixel origin
    into one consistent logical desktop coordinate system (matching
    WinForms' ``Screen.Bounds``, which is already in that space). Any other
    code translating a *global/desktop* coordinate (a window's position, a
    move() target, a position-changed event) must use this same scale for
    that origin, not the scale of whichever monitor the window happens to
    be on right now — mixing the two is what let cross-monitor moves and
    get_position()/get_screens() disagree on mixed-DPI setups.
    """
    bounds = DisplayArea.primary.outer_bounds
    return get_monitor_scale(bounds.x, bounds.y, bounds.width, bounds.height)


def _png_to_ico(png_path: str) -> str | None:
    """
    Wrap a PNG file's raw bytes in a minimal single-image .ico container.

    AppWindow.set_icon() requires an actual .ico file, unlike every other
    backend's icon setting, which accepts whatever image format the
    underlying toolkit supports (the documented public API — see
    examples/icon.py — passes a .png). Windows has accepted PNG-compressed
    icon images inside .ico containers (not just legacy BMP/DIB) since
    Vista, so no re-encoding is needed: just prepend the ICONDIR/
    ICONDIRENTRY header bytes in front of the original PNG data.

    Returns the path to a new temporary .ico file (registered for cleanup
    at exit), or None if `png_path` isn't a PNG this can wrap.
    """
    try:
        with open(png_path, 'rb') as f:
            data = f.read()

        if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) < 24:
            return None

        width, height = struct.unpack('>II', data[16:24])
        if width > 256 or height > 256:
            # ICONDIRENTRY's width/height are single bytes, with 0 meaning
            # exactly 256 - not "256 or larger". A larger image (512x512 app
            # icons are common) has no valid encoding here at all; writing 0
            # would claim 256x256 while the embedded PNG is actually bigger,
            # which set_icon() can reject as malformed. Fall back to the
            # default icon instead of risking a construction failure.
            logger.warning(
                'Window icon %r is %dx%d, larger than the 256x256 .ico format '
                'supports; falling back to the default icon.',
                png_path,
                width,
                height,
            )
            return None
        # 256 itself is encoded as 0; anything smaller fits in the byte as-is.
        icon_width = 0 if width == 256 else width
        icon_height = 0 if height == 256 else height

        icondir = struct.pack('<HHH', 0, 1, 1)
        icondirentry = struct.pack(
            '<BBBBHHII', icon_width, icon_height, 0, 0, 1, 32, len(data), len(icondir) + 16
        )

        fd, ico_path = tempfile.mkstemp(suffix='.ico')
        with os.fdopen(fd, 'wb') as f:
            f.write(icondir)
            f.write(icondirentry)
            f.write(data)

        def _cleanup():
            with contextlib.suppress(OSError):
                os.remove(ico_path)

        atexit.register(_cleanup)
        return ico_path
    except Exception:
        logger.exception('Failed to convert PNG icon %r to .ico', png_path)
        return None


class WinUI3EdgeChrome(WebView2Core):
    def __init__(self, form: Window, window: _Window, cache_dir: str):
        super().__init__(window)

        self.webview = form.content.as_(Grid).find_name('webview').as_(WebView2)
        self.form = form
        self._drag_hwnd = get_window_from_window_id(form.app_window.id)
        self.user_data_folder = cache_dir
        self._js_result_semaphores: set[Semaphore] = set()
        self._js_result_lock = Lock()
        self._is_ready = False
        self._pending_load: tuple[str, str, str] | None = None

        self.webview.add_core_webview2_initialized(self.on_webview_ready)
        self.webview.add_navigation_starting(self.on_navigation_start)
        self.webview.add_navigation_completed(self.on_navigation_completed)
        self.webview.add_web_message_received(self.on_script_notify)

        r, g, b = self._parse_hex_color(window.background_color)
        self.webview.default_background_color = Color(255, r, g, b)

        if window.transparent:
            logger.warning(
                'Transparent background is not supported on WinUI 3. See https://github.com/microsoft/microsoft-ui-xaml/issues/2992 or https://github.com/microsoft/microsoft-ui-xaml/issues/6527.'
            )

        env_options = CoreWebView2EnvironmentOptions()
        env_options.additional_browser_arguments = self._build_browser_args()

        runtime_path = webview_settings['WEBVIEW2_RUNTIME_PATH']
        if runtime_path and not os.path.isabs(runtime_path):
            runtime_path = os.path.join(get_app_root(), runtime_path)
        if runtime_path and not os.path.exists(runtime_path):
            logger.warning(
                'Custom WebView2 runtime path does not exist: %s. Using system WebView2.',
                runtime_path,
            )
            runtime_path = ''
        elif runtime_path:
            logger.debug('Using custom WebView2 runtime: %s', runtime_path)

        env_op = CoreWebView2Environment.create_with_options_async(
            runtime_path or '', cache_dir, env_options
        )

        # Only the master window's WebView2 setup gates app-wide readiness; a
        # secondary window's own failure must not abort the whole application
        # (see _fail_main_window_creation vs. _fail_child_window_creation).
        is_master = window.uid == 'master'

        def on_env_op_completed(op: IAsyncOperation[CoreWebView2Environment], status: AsyncStatus):
            if status != AsyncStatus.COMPLETED:
                error = _async_creation_error('CoreWebView2Environment', op, status)
                logger.error('%s', error)
                if is_master:
                    _fail_main_window_creation(error)
                else:
                    _fail_child_window_creation(form, window.uid)
                return

            # get_results()/controller-option creation/the ensure_core_webview2
            # call below are all synchronous and can raise (e.g. an invalid
            # runtime path, private-mode not being supported). Left
            # unguarded, that exception would escape this WinRT callback
            # without ever unblocking a thread waiting in
            # _wait_for_main_window(), the same hang class fixed elsewhere
            # for _on_launched and the child create() dispatch.
            try:
                env = op.get_results()

                ctrl_options = env.create_core_webview2_controller_options()
                ctrl_options.is_in_private_mode_enabled = _state['private_mode']

                ensure_op = self.webview.ensure_core_webview2_with_environment_and_options_async(
                    env, ctrl_options
                )
            except BaseException as error:
                logger.exception('Error setting up CoreWebView2 environment')
                if is_master:
                    _fail_main_window_creation(error)
                else:
                    _fail_child_window_creation(form, window.uid)
                return

            def on_ensure_op_completed(op: IAsyncAction, status: AsyncStatus):
                if status != AsyncStatus.COMPLETED:
                    error = _async_creation_error('CoreWebView2', op, status)
                    logger.error('%s', error)
                    if is_master:
                        _fail_main_window_creation(error)
                    else:
                        _fail_child_window_creation(form, window.uid)
                    return

                _main_window_created.set()

            ensure_op.completed = on_ensure_op_completed

        env_op.completed = on_env_op_completed

    def evaluate_js(self, script: str, parse_json: bool):
        result = None
        semaphore = Semaphore(0)
        with self._js_result_lock:
            self._js_result_semaphores.add(semaphore)

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

        def callback():
            try:
                op = self.webview.execute_script_async(script)

                def on_completed(op: IAsyncOperation[str], status: AsyncStatus):
                    if status == AsyncStatus.ERROR:
                        logger.error(
                            'Error executing script: %r',
                            WinError(op.error_code.value),
                        )
                        _callback(None)
                    elif status == AsyncStatus.CANCELED:
                        _callback(None)
                    elif status == AsyncStatus.COMPLETED:
                        try:
                            _callback(json.loads(op.get_results()))
                        except Exception:
                            logger.exception('Error parsing script result')
                            _callback(None)

                op.completed = on_completed
            except Exception:
                logger.exception('Error occurred in script')
                _callback(None)

        try:
            if self.webview.dispatcher_queue.has_thread_access:
                # Already on the UI thread (e.g. a native XAML event handler,
                # such as the custom title bar example's button click).
                # Window.evaluate_js() (parse_json=True) needs its result,
                # and blocking on the semaphore below would deadlock the
                # very dispatcher that has to run `callback` and deliver it
                # — raise *before* starting the script, not after, so a
                # caller that catches this and retries doesn't end up
                # running a script with side effects twice. Window.run_js()
                # (parse_json=False) is fire-and-forget by contract — its
                # docstring says the result isn't guaranteed — so it's the
                # only case where it's safe to start the script and return.
                if parse_json:
                    raise RuntimeError(
                        'evaluate_js() cannot return a result synchronously when called '
                        'from a native UI-thread callback (e.g. a XAML event handler) '
                        'without deadlocking the dispatcher that must deliver it.'
                    )
                callback()
                return None

            if not _enqueue(self.webview.dispatcher_queue, callback):
                return None

            semaphore.acquire()
            return result
        finally:
            with self._js_result_lock:
                self._js_result_semaphores.discard(semaphore)

    def release_pending_js_results(self):
        with self._js_result_lock:
            semaphores = tuple(self._js_result_semaphores)

        for semaphore in semaphores:
            semaphore.release()

    def clear_cookies(self):
        self.webview.core_webview2.cookie_manager.delete_all_cookies()

    def get_cookies(self, cookies: list[SimpleCookie], semaphore: Semaphore):
        def _parse_cookies(_cookies: Sequence[CoreWebView2Cookie]):
            # cookies must be accessed in the main thread, otherwise an exception is thrown
            # https://github.com/MicrosoftEdge/WebView2Feedback/issues/1976
            try:
                for c in _cookies:
                    try:
                        # Some WinRT bindings expose `same_site` as a plain int
                        # rather than the enum object — normalize via the enum
                        # constructor so .name is always available.
                        kind = CoreWebView2CookieSameSiteKind(c.same_site)
                        same_site = (
                            None
                            if kind == CoreWebView2CookieSameSiteKind.NONE
                            else kind.name.lower()
                        )
                        data = {
                            'name': c.name,
                            'value': c.value,
                            'path': c.path,
                            'domain': c.domain,
                            'expires': _format_cookie_expiry(c.expires, c.is_session),
                            'secure': c.is_secure,
                            'httponly': c.is_http_only,
                            'samesite': same_site,
                        }

                        cookie = create_cookie(data)
                        cookies.append(cookie)
                    except Exception as e:
                        logger.exception(e)
            finally:
                semaphore.release()

        try:
            op = self.webview.core_webview2.cookie_manager.get_cookies_async(self.url or '')
        except Exception:
            logger.exception('Error requesting cookies')
            semaphore.release()
            return

        def on_op_completed(op: IAsyncOperation[Sequence[CoreWebView2Cookie]], status: AsyncStatus):
            try:
                if status == AsyncStatus.ERROR:
                    logger.error(
                        'Error getting cookies: %r',
                        WinError(op.error_code.value),
                    )
                    semaphore.release()
                    return
                elif status == AsyncStatus.COMPLETED:
                    _cookies = op.get_results()

                    def callback():
                        _parse_cookies(_cookies)

                    if not _enqueue(self.webview.dispatcher_queue, callback):
                        semaphore.release()
                else:
                    semaphore.release()
            except Exception:
                logger.exception('Error in cookie completion handler')
                semaphore.release()

        op.completed = on_op_completed

    def load_html(self, content: str, base_uri: str):
        self.html = inject_base_uri(content, base_uri) if base_uri else content
        self.ishtml = True

        if not self._is_ready:
            self._pending_load = ('html', content, base_uri)
            return

        self.webview.core_webview2.navigate_to_string(self.html)

    def load_url(self, url: str):
        self.ishtml = False

        if not self._is_ready:
            self._pending_load = ('url', url, '')
            return

        self.webview.source = Uri(url)

    def on_certificate_error(
        self, _: CoreWebView2, args: CoreWebView2ServerCertificateErrorDetectedEventArgs
    ):
        args.action = CoreWebView2ServerCertificateErrorAction.ALWAYS_ALLOW

    def _show_alert(self, message: str):
        dialog = ContentDialog()
        dialog.xaml_root = self.webview.xaml_root
        dialog.content = box_string(message)
        dialog.close_button_text = self.pywebview_window.localization['global.ok']
        dialog.default_button = ContentDialogButton.CLOSE

        op = dialog.show_async()

        def on_completed(op: IAsyncOperation[ContentDialogResult], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                logger.error('Error showing ContentDialog: %r', WinError(op.error_code.value))
                return
            if status == AsyncStatus.COMPLETED:
                op.get_results()

        op.completed = on_completed

    def _extract_dropped_files(self, additional_objects) -> list:
        return [
            (os.path.basename(file.path), file.path)
            for file in [
                obj.as_(CoreWebView2File)
                for obj in additional_objects
                if obj._runtime_class_name_.endswith('CoreWebView2File')
            ]
        ]

    def _apply_settings(self, settings):
        settings.are_browser_accelerator_keys_enabled = _state['debug']
        settings.are_default_context_menus_enabled = _state['debug']
        settings.are_default_script_dialogs_enabled = True
        settings.are_dev_tools_enabled = _state['debug']
        settings.is_built_in_error_page_enabled = True
        settings.is_script_enabled = True
        settings.is_web_message_enabled = True
        settings.is_status_bar_enabled = _state['debug']
        settings.is_swipe_navigation_enabled = False
        settings.is_zoom_control_enabled = True
        if _state['user_agent']:
            settings.user_agent = _state['user_agent']

    def on_script_notify(self, sender: WebView2, args: CoreWebView2WebMessageReceivedEventArgs):
        try:
            self._route_script_message(args.web_message_as_json, lambda: args.additional_objects)
        except Exception:
            logger.exception('Exception occurred during on_script_notify')

    def on_new_window_request(
        self, sender: CoreWebView2, args: CoreWebView2NewWindowRequestedEventArgs
    ):
        args.handled = True
        self._handle_new_window_request(args.uri)

    def on_source_changed(self, sender: CoreWebView2, args: CoreWebView2SourceChangedEventArgs):
        source = sender.source or None

        if self.ishtml and source and source.lower() == 'about:blank':
            # navigate_to_string() (used by load_html) reports the source as
            # about:blank; don't let that clear HTML mode, or get_current_url()
            # would report 'about:blank' instead of None for HTML/default-
            # content windows.
            return

        self.url = source
        self.ishtml = False

    def on_webview_ready(self, sender: WebView2, args: CoreWebView2InitializedEventArgs):
        if args.exception.value:
            logger.error(
                'WebView2 initialization failed with exception:\n%s',
                WinError(args.exception.value).strerror,
            )
            return

        sender.core_webview2.add_source_changed(self.on_source_changed)
        sender.core_webview2.add_new_window_requested(self.on_new_window_request)
        sender.core_webview2.add_web_resource_requested_filter(
            '*', CoreWebView2WebResourceContext.ALL
        )
        sender.core_webview2.add_web_resource_response_received(self.on_web_resource_response)
        sender.core_webview2.add_web_resource_requested(self.on_web_resource_request)

        if self._should_ignore_ssl():
            sender.core_webview2.add_server_certificate_error_detected(self.on_certificate_error)

        sender.core_webview2.add_download_starting(self.on_download_starting)

        self._apply_settings(sender.core_webview2.settings)

        if _state['private_mode']:
            # cookies persist even if UserDataFolder is in memory. We have to delete cookies manually.
            sender.core_webview2.cookie_manager.delete_all_cookies()

        pending_load = self._pending_load
        self._pending_load = None
        self._is_ready = True

        if pending_load:
            kind, content, base_uri = pending_load
        else:
            kind, content = self._get_initial_load()
            base_uri = ''

        if kind == 'url':
            self.load_url(content)
        else:
            self.load_html(content, base_uri)

        if _state['debug'] and webview_settings['OPEN_DEVTOOLS_IN_DEBUG']:
            sender.core_webview2.open_dev_tools_window()

    def on_download_starting(
        self, sender: CoreWebView2, args: CoreWebView2DownloadStartingEventArgs
    ):
        args.cancel = True  # default: cancel; uncancelled below if user picks a file

        if not self._should_allow_download():
            return

        deferral = args.get_deferral()

        try:
            picker = FileSavePicker()
            initialize_with_window(picker, self._drag_hwnd)
            picker.suggested_start_location = PickerLocationId.DOWNLOADS
            picker.suggested_file_name = os.path.basename(args.result_file_path)
            picker.file_type_choices['*'] = ['.']

            operation = picker.pick_save_file_async()

            def on_completed(op: IAsyncOperation[StorageFile], status: AsyncStatus):
                try:
                    if status == AsyncStatus.ERROR:
                        logger.error(
                            'Error selecting download destination: %r',
                            WinError(op.error_code.value),
                        )
                    elif status == AsyncStatus.COMPLETED:
                        selected_file = op.get_results()
                        if selected_file is not None:
                            args.result_file_path = selected_file.path
                            args.cancel = False
                except Exception:
                    logger.exception('Error handling download destination')
                finally:
                    deferral.complete()

            operation.completed = on_completed
        except Exception:
            logger.exception('Error opening download destination picker')
            deferral.complete()

    def on_web_resource_response(
        self, sender: CoreWebView2, args: CoreWebView2WebResourceResponseReceivedEventArgs
    ):
        headers = {kv.key: kv.value for kv in args.response.headers}
        self._fire_response_event(args.request.uri, args.response.status_code, headers)

    def on_web_resource_request(
        self, sender: CoreWebView2, args: CoreWebView2WebResourceRequestedEventArgs
    ):
        if not len(self.pywebview_window.events.request_sent):
            return

        original_headers = {kv.key: kv.value for kv in args.request.headers}
        uri = args.request.uri
        method = args.request.method
        deferral = args.get_deferral()

        def dispatch_event():
            try:
                diff = self._compute_request_header_diff(original_headers, uri, method)
            except Exception:
                logger.exception('Error handling web resource request')
                diff = None

            def apply_header_diff():
                try:
                    if diff is not None:
                        extra, missing = diff
                        for key, value in extra.items():
                            args.request.headers.set_header(key, value)
                        for key in missing:
                            args.request.headers.remove_header(key)
                finally:
                    deferral.complete()

            if not _enqueue(self.webview.dispatcher_queue, apply_header_diff):
                deferral.complete()

        self._dispatch_request_event(dispatch_event)

    def on_navigation_start(self, sender: WebView2, args: CoreWebView2NavigationStartingEventArgs):
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
        AllowDrop="True"
        HorizontalAlignment="Stretch" VerticalAlignment="Stretch"/>
</Grid>
"""


class WinUIWindow(Window):
    # this wrapper is used for setting native.webview property
    pass


class BrowserView:
    instances: dict[str, 'BrowserForm'] = {}

    app_menu_list: Iterable[Menu] = []

    class BrowserForm:
        def __init__(self, window: _Window, cache_dir: str):
            try:
                self._construct(window, cache_dir)
            except BaseException:
                # create_guarded()'s failure handler only ever sees `window`
                # (the pywebview model), not this partially-constructed
                # `self` - a Python exception from __init__ discards the
                # instance before the caller's assignment ever completes,
                # so there is no other reference through which to close the
                # native WinRT Window this may have already created. Must
                # be cleaned up here, before re-raising, or a failure after
                # `self.window = WinUIWindow()` leaks that native window
                # and its callbacks alive forever.
                with contextlib.suppress(Exception):
                    if getattr(self, 'window', None) is not None:
                        # Bypass the closing event/confirm_close veto path,
                        # same reasoning as _fail_child_window_creation.
                        self._closing_confirmed = True
                        self.window.close()
                raise

        def _construct(self, window: _Window, cache_dir: str):
            self._is_active = False
            self._closing_confirmed = False
            self._min_size = window.min_size
            self.uid = window.uid
            self.pywebview_window = window
            self.window = WinUIWindow()
            self.handle = get_window_from_window_id(self.window.app_window.id)
            self.real_url = None

            self.pywebview_window.native = self.window

            self.window.title = window.title
            self.window.content = XamlReader.load(_WINDOW_XAML).as_(UIElement)
            scale = window.screen.scale if window.screen else self._scale
            self.window.app_window.resize(
                (
                    int(max(window.initial_width, window.min_size[0]) * scale),
                    int(max(window.initial_height, window.min_size[1]) * scale),
                )
            )

            if window.initial_x is not None and window.initial_y is not None:
                # initial_x/y are desktop-wide logical coordinates — the same
                # space get_screens() reports monitor origins in — so they
                # always convert with the single primary-monitor scale,
                # regardless of which monitor they end up landing on. Unlike
                # size below, this needs no re-resolution: the primary's
                # scale doesn't depend on where the window lands.
                self.window.app_window.move(
                    (
                        int(window.initial_x * _primary_monitor_scale()),
                        int(window.initial_y * _primary_monitor_scale()),
                    )
                )

                # The window's *size*, unlike its position, legitimately
                # depends on the real DPI of whichever monitor it actually
                # lands on — which isn't known until it's been placed there.
                # Re-resolve against the display the window actually landed
                # on and, if its scale differs from what we assumed above,
                # correct the size for the real scale.
                target_area = DisplayArea.get_from_window_id(
                    self.window.app_window.id, DisplayAreaFallback.NEAREST
                )
                target_scale = get_monitor_scale(
                    target_area.outer_bounds.x,
                    target_area.outer_bounds.y,
                    target_area.outer_bounds.width,
                    target_area.outer_bounds.height,
                )
                if target_scale != scale:
                    scale = target_scale
                    self.window.app_window.resize(
                        (
                            int(max(window.initial_width, window.min_size[0]) * scale),
                            int(max(window.initial_height, window.min_size[1]) * scale),
                        )
                    )
            elif window.screen:
                did = cast(DisplayId, window.screen.frame)
                area = DisplayArea.get_from_display_id(did)
                x = (
                    area.work_area.x
                    + (area.work_area.width - self.window.app_window.size.width) // 2
                )
                y = (
                    area.work_area.y
                    + (area.work_area.height - self.window.app_window.size.height) // 2
                )
                self.window.app_window.move((x, y))
            else:
                area = DisplayArea.get_from_window_id(
                    self.window.app_window.id, DisplayAreaFallback.NEAREST
                )
                x = (
                    area.work_area.x
                    + (area.work_area.width - self.window.app_window.size.width) // 2
                )
                y = (
                    area.work_area.y
                    + (area.work_area.height - self.window.app_window.size.height) // 2
                )
                self.window.app_window.move((x, y))

            self.full_screen_presenter = FullScreenPresenter.create()
            self.overlapped_presenter = self.window.app_window.presenter.as_(OverlappedPresenter)
            self.overlapped_presenter.is_resizable = window.resizable
            self.old_state = self.overlapped_presenter.state

            # apply windows theme to title bar
            self.window.app_window.title_bar.icon_show_options = (
                IconShowOptions.SHOW_ICON_AND_SYSTEM_MENU
            )

            # Application icon. set_icon() requires a path to an .ico file.
            # The documented public API (see examples/icon.py) passes a
            # .png, which every other backend accepts directly, so convert
            # it via _png_to_ico() rather than raising during construction.
            # There's no valid fallback when no custom icon is configured
            # (sys.executable is a .exe) — leave the icon unset and let
            # Windows fall back to the executable/package default.
            if _state['icon'] and os.path.isfile(_state['icon']):
                icon_path = _state['icon']
                if not icon_path.lower().endswith('.ico'):
                    if icon_path.lower().endswith('.png'):
                        icon_path = _png_to_ico(icon_path)
                    else:
                        logger.warning(
                            'WinUI3 only supports .ico or .png window icons, got %r. '
                            'Falling back to the default icon.',
                            _state['icon'],
                        )
                        icon_path = None
                if icon_path:
                    self.window.app_window.set_icon(icon_path)

            self.url = window.real_url

            self.overlapped_presenter.is_always_on_top = window.on_top

            if window.fullscreen:
                self.toggle_fullscreen()

            if window.frameless:
                self.overlapped_presenter.set_border_and_title_bar(False, False)
                # set_border_and_title_bar can add WS_EX_TOOLWINDOW / strip
                # WS_EX_APPWINDOW, which causes Appium/WinAppDriver (and the
                # Windows shell) to skip the window during enumeration.
                # Explicitly restore WS_EX_APPWINDOW so automation tools can
                # still find the window.
                ex_style = windll.user32.GetWindowLongW(self.handle, GWL_EXSTYLE)
                ex_style = (ex_style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                windll.user32.SetWindowLongW(self.handle, GWL_EXSTYLE, ex_style)

                if window.shadow and not window.transparent:
                    enable_window_shadow(self.handle)

            menu = window.menu or _state['menu'] or BrowserView.app_menu_list
            if menu:
                self.set_window_menu(menu)

            self.browser = WinUI3EdgeChrome(self.window, window, cache_dir)
            self.window.webview = self.browser.webview
            if not window.focus:
                windll.user32.SetWindowLongW(
                    self.handle,
                    -20,
                    windll.user32.GetWindowLongW(self.handle, -20) | 0x8000000,
                )

            self.window.add_activated(self.on_activated)
            self.window.add_closed(self.on_close)
            self.window.app_window.add_closing(self.on_closing)
            self.window.add_size_changed(self.on_resize)
            self.window.app_window.add_changed(self.on_changed)

            self.localization = window.localization

            # Installed last, once construction has fully succeeded: this
            # global WH_MOUSE_LL hook stays live system-wide until
            # uninstall_mouse_hook() runs from on_close, which only happens
            # for a form that actually made it into BrowserView.instances.
            # Installing it earlier and then having a later step raise would
            # leave the hook active with no registered instance for any
            # failure handler to find and uninstall it through — and once
            # this partially constructed form (and the ctypes callback
            # closure the hook holds a pointer to) is garbage collected,
            # Windows could still invoke that now-freed callback.
            #
            # WinUI3's XAML layer swallows WM_MOUSEWHEEL before it reaches
            # WebView2. This hook intercepts wheel events and posts them
            # directly to the WebView2 Chrome_WidgetWin_0 input HWND, and
            # also handles frameless-window dragging via SetWindowPos. The
            # returned reference must stay alive to prevent the ctypes
            # callback and hook handle from being GC'd.
            self._mouse_hook = install_mouse_hook(self.handle)

        def __str__(self):
            return f'<Window object with {self.handle} handle>'

        @property
        def _scale(self) -> float:
            """Logical-to-physical pixel scale for the monitor this window is on."""
            # GetDpiForWindow's return depends on the HWND's own effective
            # DPI_AWARENESS: for a SYSTEM_AWARE window it's a fixed system
            # DPI regardless of which monitor the window is actually on, not
            # necessarily that monitor's real DPI. setup_app() makes this
            # process SYSTEM_DPI_AWARE via SetProcessDPIAware() (per-monitor
            # v2 conflicts with pywinrt's own internal DPI context - see that
            # call site), so rather than depend on whether pywinrt's window
            # creation ends up overriding that awareness for its own HWND,
            # use get_monitor_scale() - already written to give the correct
            # answer under either awareness mode - on the window's current
            # physical bounds instead of asking GetDpiForWindow directly.
            x, y = self.window.app_window.position.unpack()
            width, height = self.window.app_window.size.unpack()
            return get_monitor_scale(x, y, width, height)

        def on_activated(self, sender: Object, args: WindowActivatedEventArgs):
            self._is_active = args.window_activation_state != WindowActivationState.DEACTIVATED

            if not self._is_active:
                return

            if not self.pywebview_window.events.shown.is_set():
                self.pywebview_window.events.shown.set()

            if not self.pywebview_window.focus:
                self.window.app_window.show_with_activation(False)

        def on_close(self, sender: Object, args: WindowEventArgs):
            if self.uid == 'master' and not _main_window_created.is_set():
                # The master window can close (e.g. from a `before_show`
                # handler) before WebView2 finishes initializing. Without
                # this, a thread blocked in _wait_for_main_window() for a
                # child window would never wake — leaving a non-daemon
                # thread alive and the process unable to exit even after
                # the WinUI application itself has shut down.
                _fail_main_window_creation(
                    RuntimeError('Main window was closed before initialization completed')
                )

            self.browser.release_pending_js_results()

            uninstall_mouse_hook(self.handle, getattr(self, '_mouse_hook', None))
            self._mouse_hook = None

            core_webview = self.browser.webview.core_webview2
            process_id = int(core_webview.browser_process_id) if core_webview else 0
            dispatcher_queue = self.window.dispatcher_queue
            exit_application = Application.current.exit
            self.browser.webview.close()

            del BrowserView.instances[self.uid]

            # during tests windows is empty for some reason. no idea why.
            if self.pywebview_window in windows:
                windows.remove(self.pywebview_window)

            self.pywebview_window.events.closed.set()

            if len(BrowserView.instances) == 0:
                if _state['private_mode']:

                    def cleanup_and_exit():
                        self.browser.clear_user_data(process_id)
                        if not _enqueue(dispatcher_queue, exit_application):
                            logger.error('Failed to exit application after private data cleanup')

                    threading.Thread(target=cleanup_and_exit, daemon=True).start()
                else:
                    exit_application()

        def on_closing(self, sender: AppWindow, args: AppWindowClosingEventArgs):
            if self._closing_confirmed:
                self._closing_confirmed = False
                return

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
                    self.window.title, self.localization['global.quitConfirmation']
                )
                op = dialog.show_async()

                def on_completed(op: IAsyncOperation[ContentDialogResult], status: AsyncStatus):
                    self.pywebview_window.events.closing -= disable_close

                    if status == AsyncStatus.ERROR:
                        logger.error(
                            'Error showing ContentDialog: %r',
                            WinError(op.error_code.value),
                        )
                        return

                    if status == AsyncStatus.COMPLETED:
                        result = op.get_results()

                        if result == ContentDialogResult.PRIMARY:
                            self._closing_confirmed = True
                            self.window.close()

                op.completed = on_completed

                # have to cancel closing so the dialog can be shown
                args.cancel = True

        def on_resize(self, sender: Object, args: WindowSizeChangedEventArgs):
            # args.size is the XAML content area's size, not the outer
            # AppWindow size get_size()/resize() use (differs by title-bar/
            # menu chrome) - use get_size() itself so events.resized always
            # agrees with what a handler reading window.get_size() would see.
            self.pywebview_window.events.resized.set(*self.get_size())

        def on_changed(self, sender: AppWindow, args: AppWindowChangedEventArgs):
            if args.did_size_change:
                scale = self._scale
                min_width = int(self._min_size[0] * scale)
                min_height = int(self._min_size[1] * scale)
                width, height = self.window.app_window.size.unpack()
                constrained_width = max(width, min_width)
                constrained_height = max(height, min_height)

                if (constrained_width, constrained_height) != (width, height):
                    self.window.app_window.resize((constrained_width, constrained_height))

            if self.overlapped_presenter.state != self.old_state:
                if self.overlapped_presenter.state == OverlappedPresenterState.MAXIMIZED:
                    self.pywebview_window.events.maximized.set()
                elif self.overlapped_presenter.state == OverlappedPresenterState.MINIMIZED:
                    self.pywebview_window.events.minimized.set()
                elif self.overlapped_presenter.state == OverlappedPresenterState.RESTORED:
                    self.pywebview_window.events.restored.set()

                self.old_state = self.overlapped_presenter.state

            if args.did_position_change:
                # Position is a desktop-wide coordinate, so it must use the
                # same primary-scale transform as get_screens()'s origins —
                # not self._scale (this window's *current* monitor), which
                # would report a different value than the Screen this
                # window is actually sitting on for a mixed-DPI setup.
                scale = _primary_monitor_scale()
                x, y = self.window.app_window.position.unpack()
                self.pywebview_window.events.moved.set(int(x / scale), int(y / scale))

        def evaluate_js(self, script: str, parse_json: bool):
            result = self.browser.evaluate_js(script, parse_json)
            return result

        def create_confirmation_dialog(self, title: str, message: str) -> ContentDialog:
            dialog = ContentDialog()
            dialog.xaml_root = self.window.content.xaml_root
            dialog.title = box_string(title)
            dialog.content = box_string(message)
            dialog.primary_button_text = self.localization['global.ok']
            dialog.close_button_text = self.localization['global.cancel']
            dialog.default_button = ContentDialogButton.PRIMARY

            return dialog

        @staticmethod
        def invoke_on_ui_thread(func):
            def wrapper(self: 'BrowserView.BrowserForm', *args, **kwargs):
                if self.window.dispatcher_queue.has_thread_access:
                    return func(self, *args, **kwargs)

                event = Event()
                result = None
                exception = None

                def invoke():
                    nonlocal result, exception

                    try:
                        result = func(self, *args, **kwargs)
                    except BaseException as ex:
                        exception = ex
                    finally:
                        event.set()

                if not _enqueue(self.window.dispatcher_queue, invoke):
                    raise RuntimeError('Failed to enqueue dispatcher callback')

                event.wait()

                if exception is not None:
                    raise exception

                return result

            return wrapper

        @invoke_on_ui_thread
        def set_title(self, title: str):
            self.window.title = title

        @invoke_on_ui_thread
        def clear_cookies(self):
            self.browser.clear_cookies()

        @invoke_on_ui_thread
        def get_cookies(self, cookies: list[SimpleCookie], semaphore: Semaphore):
            self.browser.get_cookies(cookies, semaphore)

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
                action_item.add_click(lambda s, e: threading.Thread(target=action.function).start())

                return action_item

            def create_submenu(
                title: str,
                line_items: Iterable[Menu | MenuAction | MenuSeparator],
                supermenu: MenuFlyoutSubItem | None = None,
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

            top_level_menu = self.window.content.as_(Grid).find_name('menu').as_(MenuBar)
            top_level_menu.items.clear()
            has_items = False

            for menu in menu_list:
                # '__app__' is a macOS-only menu container.
                if isinstance(menu, Menu) and menu.title == '__app__':
                    continue
                top_level_menu.items.append(create_menu_item(menu))
                has_items = True

            top_level_menu.visibility = Visibility.VISIBLE if has_items else Visibility.COLLAPSED

        @invoke_on_ui_thread
        def toggle_fullscreen(self):
            if self.window.app_window.presenter.kind == AppWindowPresenterKind.FULL_SCREEN:
                self.window.app_window.set_presenter(self.overlapped_presenter)
            else:
                self.window.app_window.set_presenter(self.full_screen_presenter)

        @invoke_on_ui_thread
        def set_on_top(self, on_top: bool):
            self.overlapped_presenter.is_always_on_top = on_top

        @invoke_on_ui_thread
        def get_size(self):
            scale = self._scale
            w, h = self.window.app_window.size.unpack()
            return (int(w / scale), int(h / scale))

        @invoke_on_ui_thread
        def resize(self, width: int, height: int, fix_point: FixPoint):
            scale = self._scale
            phys_w = int(width * scale)
            phys_h = int(height * scale)
            x, y = self.window.app_window.position.unpack()

            if fix_point & FixPoint.EAST:
                x += self.window.app_window.size.width - phys_w

            if fix_point & FixPoint.SOUTH:
                y += self.window.app_window.size.height - phys_h

            self.window.app_window.move_and_resize((x, y, phys_w, phys_h))

        @invoke_on_ui_thread
        def get_position(self):
            # Desktop-wide coordinate — must use the same primary-scale
            # transform as get_screens()'s origins, not self._scale (this
            # window's own current monitor), so this round-trips with
            # move() and matches the Screen this window is actually on.
            scale = _primary_monitor_scale()
            x, y = self.window.app_window.position.unpack()
            return (int(x / scale), int(y / scale))

        @invoke_on_ui_thread
        def move(self, x: int, y: int):
            # x/y are desktop-wide logical coordinates (e.g. from
            # get_screens() or a prior get_position()) — convert with the
            # primary monitor's scale, not self._scale (the *source*
            # monitor the window happens to be on right now), which would
            # place the window wrong whenever the destination has a
            # different DPI than the window's current position.
            scale = _primary_monitor_scale()
            self.window.app_window.move((int(x * scale), int(y * scale)))

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
_main_window_creation_error: BaseException | None = None
_app_exit_stack: contextlib.ExitStack | None = None


def _async_creation_error(component: str, operation, status: AsyncStatus) -> RuntimeError:
    if status == AsyncStatus.ERROR:
        return RuntimeError(f'Error creating {component}: {WinError(operation.error_code.value)}')
    return RuntimeError(f'Creating {component} was canceled')


def _fail_main_window_creation(error: BaseException) -> None:
    global _main_window_creation_error

    _main_window_creation_error = error
    _main_window_created.set()
    Application.current.exit()


def _fail_child_window_creation(form: Window, uid: str) -> None:
    """
    Handle a WebView2 setup failure for a non-master window: unlike the master
    window, this must not touch global creation state or exit the app — only
    the affected window is closed.

    Bypasses the normal close flow's `closing` event and `confirm_close`
    dialog (via the same `_closing_confirmed` fast path `on_closing` uses
    once a close has already been user-confirmed) — a window that failed
    to initialize must always be torn down, not left registered and
    visible because a `closing` handler vetoed it or a confirmation dialog
    is still waiting on user input.
    """
    browser = BrowserView.instances.get(uid)
    if browser is not None:
        browser._closing_confirmed = True
    with contextlib.suppress(Exception):
        form.close()


def _wait_for_main_window() -> None:
    _main_window_created.wait()
    if _main_window_creation_error is not None:
        raise RuntimeError('Main window creation failed') from _main_window_creation_error


def _close_app_runtime() -> None:
    global _app_exit_stack

    if _app_exit_stack is not None:
        try:
            _app_exit_stack.close()
        finally:
            _app_exit_stack = None


def init_storage():
    global cache_dir

    if not _state['private_mode'] or _state['storage_path']:
        try:
            try:
                # Only succeeds if the current process has package identity.
                app_data = ApplicationData.get_default()
                data_folder = app_data.shared_local_path
            except OSError:
                data_folder = os.environ.get('APPDATA') or os.path.expanduser('~')

            cache_dir = _state['storage_path'] or os.path.join(data_folder, 'pywebview')

            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
        except Exception as ex:
            logger.exception(f'Cache directory creation failed: {ex}')
    else:
        _cache_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        atexit.register(_cache_dir.cleanup)
        cache_dir = _cache_dir.name


_app_setup = False
atexit.register(_close_app_runtime)


def setup_app():
    # MUST be called before create_window and set_app_menu
    global _app_exit_stack, _app_setup, _main_window_creation_error

    if _app_setup:
        return

    _main_window_created.clear()
    _main_window_creation_error = None
    _app_exit_stack = contextlib.ExitStack()

    # System-DPI-aware mode stops the XAML compositor from being upscaled by
    # Windows, keeping text and icons crisp.  The newer per-monitor-v2 context
    # (-4) appears to conflict with how the Python WinRT bindings initialise
    # their own DPI context, so we use the older SetProcessDPIAware() instead.
    windll.user32.SetProcessDPIAware()

    try:
        init_apartment(ApartmentType.SINGLE_THREADED)
        _app_exit_stack.callback(uninit_apartment)
        _app_exit_stack.enter_context(initialize(options=InitializeOptions.ON_NO_MATCH_SHOW_UI))
    except BaseException:
        _close_app_runtime()
        raise

    _app_setup = True


def create_window(window: _Window):
    global _app_setup

    def create() -> None:
        browser = BrowserView.BrowserForm(window, cache_dir)
        BrowserView.instances[window.uid] = browser
        window.events.before_show.set()

        if window.hidden:
            browser.window.app_window.hide()
            window.events.shown.set()
        else:
            if window.focus:
                browser.window.activate()
            else:
                # activate() always takes focus; showing without activation
                # is the only way to avoid stealing it from the previously
                # focused app, since that focus can't be reliably restored
                # afterwards once activate() has already taken it.
                browser.window.app_window.show_with_activation(False)

            if not window.events.shown.is_set():
                window.events.shown.set()

        # Applies regardless of visibility, matching WinForms/GTK: a window
        # created hidden and maximized/minimized should already be in that
        # state once it's later shown, not reset to normal. Skipped when
        # fullscreen was requested: BrowserForm.__init__ already switched to
        # full_screen_presenter, and OverlappedPresenter.maximize()/minimize()
        # would switch the active presenter back to it, undoing fullscreen —
        # WinForms resolves the same combination by always applying
        # fullscreen last, so it wins regardless of maximized/minimized.
        if window.fullscreen:
            pass
        elif window.maximized:
            browser.overlapped_presenter.maximize()
        elif window.minimized:
            browser.overlapped_presenter.minimize()

    if window.uid == 'master':
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

                    try:
                        create()
                    except BaseException as error:
                        # A synchronous failure here (e.g. BrowserForm
                        # construction) would otherwise leave
                        # _main_window_created unset forever, hanging any
                        # thread blocked in _wait_for_main_window() for a
                        # child window. Route it through the same failure
                        # path as an async WebView2 setup error instead of
                        # letting it propagate out of this WinRT callback.
                        _fail_main_window_creation(error)

                def get_xaml_type(self, type: TypeName | tuple[str, TypeKind]) -> IXamlType:
                    return self._provider.get_xaml_type(type)

                def get_xaml_type_by_full_name(self, full_name: str) -> IXamlType:
                    return self._provider.get_xaml_type_by_full_name(full_name)

                def get_xmlns_definitions(self) -> Array[XmlnsDefinition]:
                    return self._provider.get_xmlns_definitions()

            App()

        try:
            Application.start(init_app)
        finally:
            BrowserView.instances.clear()
            _close_app_runtime()
            _app_setup = False
        if _main_window_creation_error is not None:
            raise RuntimeError('Main window creation failed') from _main_window_creation_error
    else:
        _wait_for_main_window()
        i = list(BrowserView.instances.values())[0]  # arbitrary instance

        def create_guarded() -> None:
            try:
                create()
            except BaseException as error:
                # Unlike the master path, a secondary window has no
                # equivalent of _fail_main_window_creation to release
                # waiters and unregister it. Without this, a failure here
                # (e.g. BrowserForm construction) would leave the window
                # in the global `windows` list forever, with `before_show`/
                # `shown`/`closed` never firing for anyone waiting on them.
                logger.error('Failed to create window %r: %s', window.uid, error)
                browser = BrowserView.instances.get(window.uid)
                if browser is not None:
                    # Already registered: close it and let on_close do its
                    # normal instances/windows/`closed` cleanup. Bypass the
                    # closing event/confirm_close veto path the same way
                    # _fail_child_window_creation does — a window that
                    # failed to construct must always be torn down.
                    browser._closing_confirmed = True
                    with contextlib.suppress(Exception):
                        browser.window.close()
                else:
                    # Construction failed before anything was registered
                    # for on_close to ever clean up.
                    if window in windows:
                        windows.remove(window)
                    window.events.closed.set()
                window.events.before_show.set()
                window.events.shown.set()

        if not _enqueue(i.window.dispatcher_queue, create_guarded):
            raise RuntimeError('Failed to enqueue callback')


def set_title(title: str, uid: str):
    i = BrowserView.instances.get(uid)

    if i:
        i.set_title(title)


def create_confirmation_dialog(title: str, message: str, uid: str) -> bool | None:
    i = BrowserView.instances.get(uid)
    if not i:
        return None

    # The dialog only needs the XAML root, which already exists once `i` is
    # available — it doesn't depend on WebView2/_main_window_created, so don't
    # wait for that here. Note this alone does not make the dialog callable
    # from a `before_show` handler: the public Window.create_confirmation_dialog
    # is separately gated on `events.shown` (@_shown_call in webview/window.py),
    # which WinUI only sets after `before_show`'s handler returns, so that path
    # still times out before ever reaching this function. This just avoids an
    # unnecessary wait for callers that *do* reach it (e.g. once shown).

    fut = Future[bool]()

    def callback():
        dialog = i.create_confirmation_dialog(title, message)

        op = dialog.show_async()

        def on_completed(op: IAsyncOperation[ContentDialogResult], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                fut.set_exception(WinError(op.error_code.value))
            elif status == AsyncStatus.CANCELED:
                fut.set_result(False)
            elif status == AsyncStatus.COMPLETED:
                result = op.get_results()
                fut.set_result(result == ContentDialogResult.PRIMARY)

        op.completed = on_completed

    return _run_dispatched(i.window.dispatcher_queue, callback, fut)


def _folder_dialog_callback(
    handle: int, allow_multiple: bool, directory: str, fut: 'Future[tuple[str, ...] | None]'
):
    def callback():
        if allow_multiple or directory:
            # FolderPicker has no multi-select API in the Windows App SDK, and no
            # way to set an initial directory (see the FIXME on create_file_dialog);
            # fall back to IFileOpenDialog (Win32 COM), which supports both.
            folders = pick_folders_win32(handle, allow_multiple=allow_multiple, directory=directory)
            fut.set_result(tuple(folders) if folders is not None else None)
            return

        picker = FolderPicker()
        initialize_with_window(picker, handle)
        picker.suggested_start_location = PickerLocationId.DOWNLOADS
        picker.file_type_filter.append('*')

        op = picker.pick_single_folder_async()

        def on_completed(op: IAsyncOperation[StorageFolder], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                fut.set_exception(WinError(op.error_code.value))
            elif status == AsyncStatus.CANCELED:
                fut.set_result(None)
            elif status == AsyncStatus.COMPLETED:
                result = op.get_results()
                if not result:
                    fut.set_result(None)
                    return
                fut.set_result((result.path,))

        op.completed = on_completed

    return callback


def _open_dialog_callback(
    handle: int,
    allow_multiple: bool,
    file_types: list[str],
    directory: str,
    fut: 'Future[tuple[str, ...] | None]',
):
    def callback():
        if directory:
            # FileOpenPicker has no way to set an initial directory (see the
            # FIXME on create_file_dialog); fall back to IFileOpenDialog
            # (Win32 COM), which supports it.
            files = pick_files_win32(handle, allow_multiple, file_types, directory)
            fut.set_result(tuple(files) if files is not None else None)
            return

        picker = FileOpenPicker()
        initialize_with_window(picker, handle)
        picker.suggested_start_location = PickerLocationId.DOWNLOADS

        if file_types:
            parsed_exts: list[str] = []
            for _, exts in [parse_file_type(f) for f in file_types]:
                for ext in exts.split(';'):
                    stripped = ext[1:]  # '*.jpg' → '.jpg'; '*.*'/'*' → '.*'/''
                    if not stripped or '*' in stripped:
                        parsed_exts = ['*']  # any wildcard → allow all
                        break
                    parsed_exts.append(stripped)
                if parsed_exts == ['*']:
                    break
            for ext in parsed_exts:
                picker.file_type_filter.append(ext)
        else:
            picker.file_type_filter.append('*')

        if allow_multiple:
            op = picker.pick_multiple_files_async()

            def on_completed(op: IAsyncOperation[Sequence[StorageFile]], status: AsyncStatus):
                if status == AsyncStatus.ERROR:
                    fut.set_exception(WinError(op.error_code.value))
                elif status == AsyncStatus.CANCELED:
                    fut.set_result(None)
                elif status == AsyncStatus.COMPLETED:
                    result = op.get_results()
                    if result is None or len(result) == 0:
                        fut.set_result(None)
                        return
                    fut.set_result(tuple(f.path for f in result))

            op.completed = on_completed
        else:
            op = picker.pick_single_file_async()

            def on_completed(op: IAsyncOperation[StorageFile], status: AsyncStatus):
                if status == AsyncStatus.ERROR:
                    fut.set_exception(WinError(op.error_code.value))
                elif status == AsyncStatus.CANCELED:
                    fut.set_result(None)
                elif status == AsyncStatus.COMPLETED:
                    result = op.get_results()
                    if not result:
                        fut.set_result(None)
                        return
                    fut.set_result((result.path,))

            op.completed = on_completed

    return callback


def _save_dialog_callback(
    handle: int,
    uid: str,
    save_filename: str,
    file_types: list[str],
    directory: str,
    fut: 'Future[tuple[str, ...] | None]',
):
    def callback():
        if directory:
            # FileSavePicker has no way to set an initial directory (see the
            # FIXME on create_file_dialog); fall back to IFileSaveDialog
            # (Win32 COM), which supports it.
            path = pick_save_file_win32(handle, save_filename, file_types, directory)
            fut.set_result((path,) if path else None)
            return

        picker = FileSavePicker()
        initialize_with_window(picker, handle)
        picker.suggested_start_location = PickerLocationId.DOWNLOADS
        picker.settings_identifier = uid
        picker.suggested_file_name = save_filename

        if file_types:
            for description, patterns in map(parse_file_type, file_types):
                extensions = []
                for pattern in patterns.split(';'):
                    extension = pattern[1:]  # '*.jpg' → '.jpg'
                    if not extension or '*' in extension:
                        extensions = ['.']
                        break
                    extensions.append(extension)
                picker.file_type_choices[description] = extensions
        else:
            # winui3 doesn't allow wildcard file types in save dialog; use a
            # non-empty label so the type entry isn't left blank in the picker.
            picker.file_type_choices['*'] = ['.']

        op = picker.pick_save_file_async()

        def on_completed(op: IAsyncOperation[StorageFile], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                fut.set_exception(WinError(op.error_code.value))
            elif status == AsyncStatus.CANCELED:
                fut.set_result(None)
            elif status == AsyncStatus.COMPLETED:
                result = op.get_results()
                if not result:
                    fut.set_result(None)
                    return
                fut.set_result((result.path,))

        op.completed = on_completed

    return callback


def create_file_dialog(
    dialog_type: int,
    directory: str,
    allow_multiple: bool,
    save_filename: str,
    file_types: list[str],
    uid: str,
) -> tuple[str, ...] | None:
    i = BrowserView.instances.get(uid)
    if not i:
        return None

    # The WinRT pickers used below have no API to set a starting location
    # (https://github.com/microsoft/WindowsAppSDK/issues/88), so whenever an
    # initial `directory` is requested we fall back to the equivalent Win32
    # IFileDialog (see webview.platforms.win32), which does support it.

    fut: Future[tuple[str, ...] | None] = Future()

    # Mirrors each callback's own `if directory: ...`/`if allow_multiple or
    # directory: ...` branch below: only that Win32 IFileDialog fallback
    # path pumps its own modal loop and resolves `fut` synchronously — the
    # WinRT picker path taken otherwise is genuinely async-only.
    if dialog_type == FileDialog.FOLDER:
        callback = _folder_dialog_callback(i.handle, allow_multiple, directory, fut)
        may_complete_synchronously = bool(allow_multiple or directory)
    elif dialog_type == FileDialog.OPEN:
        callback = _open_dialog_callback(i.handle, allow_multiple, file_types, directory, fut)
        may_complete_synchronously = bool(directory)
    elif dialog_type == FileDialog.SAVE:
        callback = _save_dialog_callback(i.handle, uid, save_filename, file_types, directory, fut)
        may_complete_synchronously = bool(directory)
    else:
        raise ValueError('Invalid dialog type')

    return _run_dispatched(i.window.dispatcher_queue, callback, fut, may_complete_synchronously)


def clear_cookies(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.clear_cookies()


def get_cookies(uid: str):
    i = BrowserView.instances.get(uid)
    if not i:
        return

    if i.window.dispatcher_queue.has_thread_access:
        # i.get_cookies() (via invoke_on_ui_thread) would run inline here and
        # only start the async cookie lookup; its completion is delivered by
        # enqueueing back onto this same dispatcher, which the acquire() below
        # would then block from ever running. Raise rather than deadlock or
        # silently return None, which would look like "no cookies" instead
        # of "unavailable in this calling context".
        raise RuntimeError(
            'get_cookies() cannot be awaited synchronously from a native UI-thread '
            'callback (e.g. a XAML event handler) without deadlocking the dispatcher '
            'that must deliver the result.'
        )

    semaphore = Semaphore(0)
    cookies: list[SimpleCookie] = []

    i.get_cookies(cookies, semaphore)

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
    """Get all screens with coordinates in logical pixels."""
    # Can't directly iterate return value of find_all(). Workaround is to
    # get by index. https://github.com/microsoft/microsoft-ui-xaml/issues/6454
    projected_displays = DisplayArea.find_all()
    all_displays = [projected_displays[i] for i in range(len(projected_displays))]
    # webview.screens documents the primary display as the first element;
    # find_all()'s native enumeration order makes no such guarantee. Sort
    # only after materializing into a real Python list above - sorted()
    # itself needs to iterate its input, which the projected collection
    # doesn't support directly.
    all_displays = sorted(all_displays, key=lambda da: not da.is_primary)

    # DisplayArea.outer_bounds reports true physical-pixel positions: e.g. a
    # 200%-scaled secondary monitor placed right after a 1920-wide primary
    # begins at physical x=1920, not some DPI-adjusted value. Converting
    # each monitor's own *origin* using its own scale therefore produces an
    # inconsistent shared coordinate system (that secondary would be
    # reported at logical x=960, overlapping the primary).
    #
    # Using the primary's scale for origins alone isn't enough either: it
    # only avoids overlap when the neighbor's own scale is >= the primary's.
    # A lower-scaled monitor placed adjacent to a higher-scaled primary
    # (e.g. a 100%-scaled screen to the left of a 200%-scaled primary) would
    # still get an origin+width combination that overlaps the primary,
    # because origin and size would be measured in two different reference
    # scales. The only way to preserve true physical adjacency for *any*
    # topology is to convert every screen's entire bounding box - origin
    # *and* size - through the same single scale, matching how Windows
    # itself virtualizes monitor bounds for system-DPI-aware processes
    # (which this module is, via SetProcessDPIAware()) and how WinForms'
    # Screen.Bounds is already reported. Each monitor's own real scale is
    # still reported separately via Screen.scale/dpi.
    primary_scale = _primary_monitor_scale()

    screens = []
    for da in all_displays:
        phys_x = da.outer_bounds.x
        phys_y = da.outer_bounds.y
        phys_width = da.outer_bounds.width
        phys_height = da.outer_bounds.height

        scale = get_monitor_scale(phys_x, phys_y, phys_width, phys_height)

        logical_x = int(phys_x / primary_scale)
        logical_y = int(phys_y / primary_scale)
        logical_width = int(phys_width / primary_scale)
        logical_height = int(phys_height / primary_scale)

        screens.append(
            Screen(
                logical_x,
                logical_y,
                logical_width,
                logical_height,
                da.display_id,
                scale,
                origin_scale=primary_scale,
            )
        )

    return screens


def add_tls_cert(_):
    return
