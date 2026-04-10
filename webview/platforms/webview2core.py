import ctypes
import json
import logging
import shutil
import webbrowser
from abc import ABC, abstractmethod
from threading import Semaphore

from webview import _state
from webview import settings as webview_settings
from webview.dom import _dnd_state
from webview.models import Request, Response
from webview.platforms.win32 import start_drag
from webview.util import DEFAULT_HTML, js_bridge_call

logger = logging.getLogger('pywebview')


class WebView2Core(ABC):
    """
    Framework-agnostic base for WebView2 backends (WinForms and WinUI3).

    Contains shared state and pure-Python logic. All .NET/WinRT calls are
    delegated to abstract methods implemented by each concrete subclass.
    """

    def __init__(self, window):
        self.pywebview_window = window
        self.url = None
        self.ishtml = False
        self.html = DEFAULT_HTML
        self.js_result_semaphore = Semaphore(0)

    def get_current_url(self):
        return self.url

    def _build_browser_args(self) -> str:
        """Build AdditionalBrowserArguments string from current webview settings."""
        args = '--disable-features=ElasticOverscroll'
        if webview_settings['ALLOW_FILE_URLS']:
            args += ' --allow-file-access-from-files'
        if webview_settings['REMOTE_DEBUGGING_PORT'] is not None:
            args += f' --remote-debugging-port={webview_settings["REMOTE_DEBUGGING_PORT"]}'
        return args

    def _should_ignore_ssl(self) -> bool:
        return _state['ssl'] or webview_settings['IGNORE_SSL_ERRORS']

    def _parse_hex_color(self, hex_color: str) -> tuple:
        c = hex_color.lstrip('#')
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

    def _get_initial_load(self) -> tuple:
        """Return ('url'|'html'|'default', content) for the first navigation."""
        if self.pywebview_window.real_url:
            return 'url', self.pywebview_window.real_url
        elif self.pywebview_window.html:
            self.html = self.pywebview_window.html
            return 'html', self.pywebview_window.html
        return 'default', DEFAULT_HTML

    def _route_script_message(self, message_json: str, additional_objects) -> None:
        """Route an incoming WebMessage to DnD, alert, console, or JS bridge."""
        if message_json == '"FilesDropped"':
            if _dnd_state['num_listeners'] == 0:
                return
            if additional_objects is None:
                return
            _dnd_state['paths'] += self._extract_dropped_files(additional_objects)
            return

        func_name, func_param, value_id = json.loads(message_json)
        func_param = json.loads(func_param)

        if func_name == '_pywebviewAlert':
            self._show_alert(str(func_param))
        elif func_name == 'pywebviewStartDrag':
            start_drag(self._drag_hwnd)
        elif func_name == 'console':
            print(func_param)
        else:
            js_bridge_call(self.pywebview_window, func_name, func_param, value_id)

    def _compute_request_header_diff(self, original: dict, uri: str, method: str):
        """
        Fire request_sent event and return (extra, missing) header diffs if changed.
        Returns None if headers are unchanged.
        """
        request = Request(uri, method, dict(original))
        self.pywebview_window.events.request_sent.set(request)
        if request.headers == original:
            return None
        extra = {k: v for k, v in request.headers.items() if k not in original or original[k] != v}
        missing = {k for k in original if k not in request.headers}
        return extra, missing

    def _fire_response_event(self, uri: str, status_code: int, headers: dict) -> None:
        response = Response(uri, status_code, headers)
        self.pywebview_window.events.response_received.set(response)

    def _should_allow_download(self) -> bool:
        return bool(webview_settings['ALLOW_DOWNLOADS'])

    def _get_download_initial_dir(self) -> str | None:
        """Read the default downloads folder path from the Windows registry."""
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',
            ) as key:
                return winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        except Exception:
            return None

    def clear_user_data(self, process_id: int) -> None:
        if not _state['private_mode']:
            return

        try:
            handle = None

            if process_id:
                handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, process_id)
            if handle:
                ctypes.windll.kernel32.WaitForSingleObject(handle, 5000)
                ctypes.windll.kernel32.CloseHandle(handle)

            shutil.rmtree(self.user_data_folder)
            logger.debug(f'Cleared user data folder: {self.user_data_folder}')
        except Exception as e:
            logger.warning(f'Failed to delete user data folder: {e}')

    def _handle_new_window_request(self, uri: str) -> None:
        if webview_settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']:
            webbrowser.open(uri)
        else:
            self.load_url(uri)

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def _show_alert(self, message: str): ...

    @abstractmethod
    def _extract_dropped_files(self, additional_objects) -> list: ...

    @abstractmethod
    def evaluate_js(self, script: str, parse_json: bool): ...

    @abstractmethod
    def load_html(self, content: str, base_uri: str): ...

    @abstractmethod
    def load_url(self, url: str): ...

    @abstractmethod
    def clear_cookies(self): ...

    @abstractmethod
    def get_cookies(self, cookies, semaphore): ...
