from enum import IntEnum
from typing import Optional, Callable, Any
import json
import ctypes
from ._webview_ffi import _webview_lib, _encode_c_string

class SizeHint(IntEnum):
    NONE = 0
    MIN = 1
    MAX = 2
    FIXED = 3

class Size:
    def __init__(self, width: int, height: int, hint: SizeHint):
        self.width = width
        self.height = height
        self.hint = hint

class Webview:
    def __init__(self, debug: bool = False, size: Optional[Size] = None, window: Optional[int] = None):
        self._handle = _webview_lib.webview_create(int(debug), window)
        self._callbacks = {}

        if size:
            self.size = size

    @property
    def size(self) -> Size:
        return self._size

    @size.setter
    def size(self, value: Size):
        _webview_lib.webview_set_size(self._handle, value.width, value.height, value.hint)
        self._size = value

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        _webview_lib.webview_set_title(self._handle, _encode_c_string(value))
        self._title = value

    def destroy(self):
        for name in list(self._callbacks.keys()):
            self.unbind(name)
        _webview_lib.webview_terminate(self._handle)
        _webview_lib.webview_destroy(self._handle)
        self._handle = None

    def navigate(self, url: str):
        _webview_lib.webview_navigate(self._handle, _encode_c_string(url))

    def run(self):
        _webview_lib.webview_run(self._handle)
        self.destroy()

    def bind(self, name: str, callback: Callable[..., Any]):
        def wrapper(seq: bytes, req: bytes, arg: int):
            args = json.loads(req.decode())
            try:
                result = callback(*args)
                success = True
            except Exception as e:
                result = str(e)
                success = False
            self.return_(seq.decode(), 0 if success else 1, json.dumps(result))

        c_callback = _webview_lib.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p)(wrapper)
        self._callbacks[name] = c_callback
        _webview_lib.webview_bind(self._handle, _encode_c_string(name), c_callback, None)

    def unbind(self, name: str):
        if name in self._callbacks:
            _webview_lib.webview_unbind(self._handle, _encode_c_string(name))
            del self._callbacks[name]

    def return_(self, seq: str, status: int, result: str):
        _webview_lib.webview_return(self._handle, _encode_c_string(seq), status, _encode_c_string(result))

    def eval(self, source: str):
        _webview_lib.webview_eval(self._handle, _encode_c_string(source))

    def init(self, source: str):
        _webview_lib.webview_init(self._handle, _encode_c_string(source))

if __name__ == "__main__":
    wv = Webview()
    wv.title = "Hello, World!"
    wv.navigate("https://www.google.com")
    wv.run()
