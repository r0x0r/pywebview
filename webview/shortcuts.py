"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/imattau/pywebview2/

Global keyboard shortcuts: hotkeys that fire even when no pywebview2 window
is focused. Implemented natively per platform: RegisterHotKey via ctypes
(Windows), the Carbon Event Manager via ctypes (macOS -- deprecated but
still functional and, unlike the modern replacement, doesn't require
requesting Accessibility permission), and XGrabKey via python-xlib (Linux,
X11 only -- there is no portable Wayland equivalent without a
compositor-specific portal, so this does not work under Wayland).
"""

from __future__ import annotations

import ctypes
import sys
import threading
from typing import Callable

from webview.errors import WebViewException

_MODIFIER_ALIASES = {
    'ctrl': 'ctrl',
    'control': 'ctrl',
    'alt': 'alt',
    'option': 'alt',
    'shift': 'shift',
    'super': 'super',
    'cmd': 'super',
    'command': 'super',
    'win': 'super',
    'meta': 'super',
    'cmdorctrl': 'cmdorctrl',
    'commandorcontrol': 'cmdorctrl',
}

# shortcut string (lowercased) -> opaque platform-specific hotkey id
_registry: dict[str, int] = {}


def _parse_shortcut(shortcut: str) -> tuple[frozenset[str], str]:
    parts = [p.strip().lower() for p in shortcut.split('+') if p.strip()]
    if len(parts) < 1:
        raise WebViewException(f'Invalid shortcut: {shortcut!r}')

    *mod_parts, key = parts
    if not key:
        raise WebViewException(f'Invalid shortcut: {shortcut!r}')

    modifiers = set()
    for part in mod_parts:
        if part not in _MODIFIER_ALIASES:
            raise WebViewException(f'Unknown modifier {part!r} in shortcut {shortcut!r}')
        canonical = _MODIFIER_ALIASES[part]
        if canonical == 'cmdorctrl':
            canonical = 'super' if sys.platform == 'darwin' else 'ctrl'
        modifiers.add(canonical)

    return frozenset(modifiers), key


def register(shortcut: str, callback: Callable[[], None]) -> None:
    """
    Register a global keyboard shortcut. Fires `callback` (in a background
    thread) whenever the shortcut is pressed, even if no pywebview2 window is
    focused.

    :param shortcut: A '+'-separated shortcut string, e.g. "ctrl+shift+s" or
        "cmdorctrl+k" (resolves to "super" on macOS, "ctrl" elsewhere).
        Modifiers: ctrl/control, alt/option, shift, super/cmd/command/win/meta.
        Keys: single alphanumeric characters, f1-f12, space, tab,
        escape/esc, enter/return, up/down/left/right, backspace, delete.
    :param callback: Called with no arguments when the shortcut fires.
    """
    if shortcut.lower() in _registry:
        raise WebViewException(f'Shortcut {shortcut!r} is already registered')

    modifiers, key = _parse_shortcut(shortcut)

    if sys.platform == 'darwin':
        hotkey_id = _macos_register(modifiers, key, callback)
    elif sys.platform == 'win32':
        hotkey_id = _windows_register(modifiers, key, callback)
    elif sys.platform.startswith('linux'):
        hotkey_id = _linux_register(modifiers, key, callback)
    else:
        raise WebViewException(f'Global shortcuts are not supported on platform {sys.platform!r}')

    _registry[shortcut.lower()] = hotkey_id


def unregister(shortcut: str) -> None:
    """Unregister a previously registered global shortcut. No-op if not registered."""
    hotkey_id = _registry.pop(shortcut.lower(), None)
    if hotkey_id is None:
        return

    if sys.platform == 'darwin':
        _macos_unregister(hotkey_id)
    elif sys.platform == 'win32':
        _windows_unregister(hotkey_id)
    elif sys.platform.startswith('linux'):
        _linux_unregister(hotkey_id)


def unregister_all() -> None:
    """Unregister all currently registered global shortcuts."""
    for shortcut in list(_registry.keys()):
        unregister(shortcut)


def is_registered(shortcut: str) -> bool:
    """Check whether a shortcut is currently registered."""
    return shortcut.lower() in _registry


def _run_callback(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, daemon=True).start()


# -- Windows: RegisterHotKey via ctypes (no new dependency) --------------------------------

_windows_registered: dict[int, Callable[[], None]] = {}
_windows_next_id = 1
_windows_thread_started = False
_windows_thread_lock = threading.Lock()
_windows_request_queue = None  # type: ignore[assignment]

_WIN_KEYCODES = {
    'space': 0x20,
    'tab': 0x09,
    'escape': 0x1B,
    'esc': 0x1B,
    'enter': 0x0D,
    'return': 0x0D,
    'up': 0x26,
    'down': 0x28,
    'left': 0x25,
    'right': 0x27,
    'backspace': 0x08,
    'delete': 0x2E,
    **{f'f{i}': 0x6F + i for i in range(1, 13)},
}


def _win_key_to_vk(key: str) -> int:
    if key in _WIN_KEYCODES:
        return _WIN_KEYCODES[key]
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    raise WebViewException(f'Unsupported key: {key!r}')


def _windows_ensure_thread() -> None:
    global _windows_thread_started, _windows_request_queue
    with _windows_thread_lock:
        if _windows_thread_started:
            return

        import queue

        _windows_request_queue = queue.Queue()
        threading.Thread(target=_windows_message_loop, daemon=True).start()
        _windows_thread_started = True


def _windows_message_loop() -> None:
    import queue
    import time
    from ctypes import byref, windll, wintypes

    user32 = windll.user32
    WM_HOTKEY = 0x0312
    PM_REMOVE = 0x0001

    while True:
        try:
            while True:
                fn, result_queue = _windows_request_queue.get_nowait()
                try:
                    result_queue.put(('ok', fn(user32)))
                except Exception as e:  # noqa: BLE001 -- forwarded to the caller's thread
                    result_queue.put(('error', e))
        except queue.Empty:
            pass

        msg = wintypes.MSG()
        while user32.PeekMessageW(byref(msg), None, 0, 0, PM_REMOVE):
            if msg.message == WM_HOTKEY:
                callback = _windows_registered.get(msg.wParam)
                if callback:
                    _run_callback(callback)

        time.sleep(0.02)


def _windows_call(fn: Callable) -> object:
    import queue

    _windows_ensure_thread()
    result_queue = queue.Queue()
    _windows_request_queue.put((fn, result_queue))
    status, value = result_queue.get(timeout=5)
    if status == 'error':
        raise value
    return value


def _windows_register(modifiers: frozenset[str], key: str, callback: Callable[[], None]) -> int:
    vk = _win_key_to_vk(key)

    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x0008, 0x4000
    mod_flags = MOD_NOREPEAT
    if 'alt' in modifiers:
        mod_flags |= MOD_ALT
    if 'ctrl' in modifiers:
        mod_flags |= MOD_CONTROL
    if 'shift' in modifiers:
        mod_flags |= MOD_SHIFT
    if 'super' in modifiers:
        mod_flags |= MOD_WIN

    global _windows_next_id
    hotkey_id = _windows_next_id
    _windows_next_id += 1

    def _do_register(user32):
        ok = user32.RegisterHotKey(None, hotkey_id, mod_flags, vk)
        if not ok:
            raise WebViewException(
                f'Failed to register hotkey (GetLastError={ctypes.GetLastError()})'
            )
        return hotkey_id

    _windows_call(_do_register)
    _windows_registered[hotkey_id] = callback
    return hotkey_id


def _windows_unregister(hotkey_id: int) -> None:
    _windows_registered.pop(hotkey_id, None)

    def _do_unregister(user32):
        user32.UnregisterHotKey(None, hotkey_id)

    _windows_call(_do_unregister)


# -- macOS: Carbon Event Manager via ctypes (no new dependency) ----------------------------

_macos_registered: dict[int, Callable[[], None]] = {}
_macos_hotkey_refs: dict[int, object] = {}
_macos_next_id = 1
_macos_handler_installed = False
_macos_handler_refs: list = []  # keeps CFUNCTYPE instances alive

_MAC_KEYCODES = {
    'a': 0x00,
    'b': 0x0B,
    'c': 0x08,
    'd': 0x02,
    'e': 0x0E,
    'f': 0x03,
    'g': 0x05,
    'h': 0x04,
    'i': 0x22,
    'j': 0x26,
    'k': 0x28,
    'l': 0x25,
    'm': 0x2E,
    'n': 0x2D,
    'o': 0x1F,
    'p': 0x23,
    'q': 0x0C,
    'r': 0x0F,
    's': 0x01,
    't': 0x11,
    'u': 0x20,
    'v': 0x09,
    'w': 0x0D,
    'x': 0x07,
    'y': 0x10,
    'z': 0x06,
    '0': 0x1D,
    '1': 0x12,
    '2': 0x13,
    '3': 0x14,
    '4': 0x15,
    '5': 0x17,
    '6': 0x16,
    '7': 0x1A,
    '8': 0x1C,
    '9': 0x19,
    'space': 0x31,
    'tab': 0x30,
    'escape': 0x35,
    'esc': 0x35,
    'enter': 0x24,
    'return': 0x24,
    'up': 0x7E,
    'down': 0x7D,
    'left': 0x7B,
    'right': 0x7C,
    'backspace': 0x33,
    'delete': 0x75,
    'f1': 0x7A,
    'f2': 0x78,
    'f3': 0x63,
    'f4': 0x76,
    'f5': 0x60,
    'f6': 0x61,
    'f7': 0x62,
    'f8': 0x64,
    'f9': 0x65,
    'f10': 0x6D,
    'f11': 0x67,
    'f12': 0x6F,
}

_CMD_KEY, _SHIFT_KEY, _OPTION_KEY, _CONTROL_KEY = 0x0100, 0x0200, 0x0800, 0x1000


def _four_char_code(s: str) -> int:
    return (ord(s[0]) << 24) | (ord(s[1]) << 16) | (ord(s[2]) << 8) | ord(s[3])


_carbon = None


def _load_carbon():
    # ctypes defaults every undeclared argument/return type to a 32-bit
    # c_int, which silently truncates the 64-bit pointers Carbon's API
    # traffics in (EventTargetRef, EventHandlerRef, ...) on 64-bit macOS --
    # corrupting memory rather than raising, since ctypes has no way to
    # detect the mismatch. Every function used here MUST have explicit
    # argtypes/restype set before its first call, which is why this is
    # done once, centrally, right after loading the library.
    global _carbon
    if _carbon is not None:
        return _carbon

    carbon = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Carbon.framework/Carbon')

    carbon.GetApplicationEventTarget.argtypes = []
    carbon.GetApplicationEventTarget.restype = ctypes.c_void_p

    carbon.InstallEventHandler.argtypes = [
        ctypes.c_void_p,  # EventTargetRef
        ctypes.c_void_p,  # EventHandlerUPP (function pointer)
        ctypes.c_uint32,  # ItemCount
        ctypes.c_void_p,  # const EventTypeSpec*
        ctypes.c_void_p,  # void* userData
        ctypes.c_void_p,  # EventHandlerRef* (out)
    ]
    carbon.InstallEventHandler.restype = ctypes.c_int32

    carbon.RegisterEventHotKey.argtypes = [
        ctypes.c_uint32,  # UInt32 inHotKeyCode
        ctypes.c_uint32,  # UInt32 inHotKeyModifiers
        _EventHotKeyID,  # EventHotKeyID inHotKeyID (by value)
        ctypes.c_void_p,  # EventTargetRef inTarget
        ctypes.c_uint32,  # OptionBits inOptions
        ctypes.c_void_p,  # EventHotKeyRef* (out)
    ]
    carbon.RegisterEventHotKey.restype = ctypes.c_int32

    carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
    carbon.UnregisterEventHotKey.restype = ctypes.c_int32

    carbon.GetEventParameter.argtypes = [
        ctypes.c_void_p,  # EventRef
        ctypes.c_uint32,  # EventParamName
        ctypes.c_uint32,  # EventParamType
        ctypes.c_void_p,  # EventParamType* actualType (out, unused)
        ctypes.c_uint32,  # UInt32 bufferSize
        ctypes.c_void_p,  # UInt32* actualSize (out, unused)
        ctypes.c_void_p,  # void* outData
    ]
    carbon.GetEventParameter.restype = ctypes.c_int32

    _carbon = carbon
    return carbon


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [('signature', ctypes.c_uint32), ('id', ctypes.c_uint32)]


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [('eventClass', ctypes.c_uint32), ('eventKind', ctypes.c_uint32)]


def _macos_install_handler(carbon) -> None:
    global _macos_handler_installed
    if _macos_handler_installed:
        return

    handler_type = ctypes.CFUNCTYPE(
        ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
    )

    def _handler(_next_handler, event, _user_data):
        hotkey_id = _EventHotKeyID()
        carbon.GetEventParameter(
            event,
            _four_char_code('----'),
            _four_char_code('hkid'),
            None,
            ctypes.sizeof(_EventHotKeyID),
            None,
            ctypes.byref(hotkey_id),
        )
        callback = _macos_registered.get(hotkey_id.id)
        if callback:
            _run_callback(callback)
        return 0

    handler_fn = handler_type(_handler)
    _macos_handler_refs.append(handler_fn)

    event_type = _EventTypeSpec(
        _four_char_code('keyb'), 5
    )  # kEventClassKeyboard, kEventHotKeyPressed
    out_ref = ctypes.c_void_p()
    status = carbon.InstallEventHandler(
        carbon.GetApplicationEventTarget(),
        handler_fn,
        1,
        ctypes.byref(event_type),
        None,
        ctypes.byref(out_ref),
    )
    if status != 0:
        raise WebViewException(f'Failed to install hotkey event handler (OSStatus={status})')
    _macos_handler_installed = True


def _macos_register(modifiers: frozenset[str], key: str, callback: Callable[[], None]) -> int:
    if key not in _MAC_KEYCODES:
        raise WebViewException(f'Unsupported key: {key!r}')

    carbon = _load_carbon()
    _macos_install_handler(carbon)

    mod_flags = 0
    if 'super' in modifiers:
        mod_flags |= _CMD_KEY
    if 'shift' in modifiers:
        mod_flags |= _SHIFT_KEY
    if 'alt' in modifiers:
        mod_flags |= _OPTION_KEY
    if 'ctrl' in modifiers:
        mod_flags |= _CONTROL_KEY

    global _macos_next_id
    hotkey_id = _macos_next_id
    _macos_next_id += 1

    hotkey_id_struct = _EventHotKeyID(_four_char_code('pywv'), hotkey_id)
    hotkey_ref = ctypes.c_void_p()

    status = carbon.RegisterEventHotKey(
        _MAC_KEYCODES[key],
        mod_flags,
        hotkey_id_struct,
        carbon.GetApplicationEventTarget(),
        0,
        ctypes.byref(hotkey_ref),
    )
    if status != 0:
        raise WebViewException(f'Failed to register hotkey (OSStatus={status})')

    _macos_registered[hotkey_id] = callback
    _macos_hotkey_refs[hotkey_id] = hotkey_ref
    return hotkey_id


def _macos_unregister(hotkey_id: int) -> None:
    carbon = _load_carbon()
    ref = _macos_hotkey_refs.pop(hotkey_id, None)
    _macos_registered.pop(hotkey_id, None)
    if ref is not None:
        carbon.UnregisterEventHotKey(ref)


# -- Linux: XGrabKey via python-xlib (X11 only, new optional dependency) -------------------

_linux_display = None
_linux_thread_started = False
_linux_thread_lock = threading.Lock()
_linux_registered: dict[tuple[int, int], Callable[[], None]] = {}
_linux_id_to_key: dict[int, tuple[int, int]] = {}
_linux_next_id = 1

# XGrabKey only matches the exact modifier mask given -- if NumLock/CapsLock
# happen to be on, the actual event modifier state includes their bits too,
# so each shortcut must be grabbed once per combination of these "ignored"
# modifiers or it silently won't fire whenever either lock key is active.
_LOCK_MASK = 1 << 1  # X.LockMask (CapsLock)
_NUM_LOCK_MASK = 1 << 4  # Mod2Mask (NumLock, on most systems)
_IGNORED_MODIFIER_COMBOS = (0, _LOCK_MASK, _NUM_LOCK_MASK, _LOCK_MASK | _NUM_LOCK_MASK)

_LINUX_KEYSYM_NAMES = {
    'escape': 'Escape',
    'esc': 'Escape',
    'enter': 'Return',
    'return': 'Return',
    'space': 'space',
    'tab': 'Tab',
    'up': 'Up',
    'down': 'Down',
    'left': 'Left',
    'right': 'Right',
    'backspace': 'BackSpace',
    'delete': 'Delete',
}


def _linux_keysym_name(key: str) -> str:
    if key in _LINUX_KEYSYM_NAMES:
        return _LINUX_KEYSYM_NAMES[key]
    if len(key) == 1:
        return key
    if key.startswith('f') and key[1:].isdigit():
        return key.upper()
    raise WebViewException(f'Unsupported key: {key!r}')


def _linux_import_xlib():
    try:
        from Xlib import XK, X
        from Xlib.display import Display
    except ImportError as e:
        raise WebViewException(
            'Global shortcuts require python-xlib on Linux (X11 only -- not supported under '
            'Wayland). Install it with "pip install pywebview2[shortcuts]".'
        ) from e
    return X, XK, Display


def _linux_ensure_thread() -> None:
    global _linux_display, _linux_thread_started
    with _linux_thread_lock:
        if _linux_thread_started:
            return

        _, _, Display = _linux_import_xlib()
        _linux_display = Display()
        threading.Thread(target=_linux_event_loop, daemon=True).start()
        _linux_thread_started = True


def _linux_event_loop() -> None:
    X, _, _ = _linux_import_xlib()

    root = _linux_display.screen().root
    root.change_attributes(event_mask=X.KeyPressMask)

    while True:
        event = _linux_display.next_event()
        if event.type == X.KeyPress:
            key = (event.detail, event.state & ~(_LOCK_MASK | _NUM_LOCK_MASK))
            callback = _linux_registered.get(key)
            if callback:
                _run_callback(callback)


def _linux_register(modifiers: frozenset[str], key: str, callback: Callable[[], None]) -> int:
    X, XK, _ = _linux_import_xlib()
    _linux_ensure_thread()

    keysym = XK.string_to_keysym(_linux_keysym_name(key))
    if keysym == 0:
        raise WebViewException(f'Unsupported key: {key!r}')
    keycode = _linux_display.keysym_to_keycode(keysym)

    mod_mask = 0
    if 'shift' in modifiers:
        mod_mask |= X.ShiftMask
    if 'ctrl' in modifiers:
        mod_mask |= X.ControlMask
    if 'alt' in modifiers:
        mod_mask |= X.Mod1Mask
    if 'super' in modifiers:
        mod_mask |= X.Mod4Mask

    root = _linux_display.screen().root
    for extra in _IGNORED_MODIFIER_COMBOS:
        root.grab_key(keycode, mod_mask | extra, True, X.GrabModeAsync, X.GrabModeAsync)
    _linux_display.sync()

    global _linux_next_id
    hotkey_id = _linux_next_id
    _linux_next_id += 1

    _linux_registered[(keycode, mod_mask)] = callback
    _linux_id_to_key[hotkey_id] = (keycode, mod_mask)
    return hotkey_id


def _linux_unregister(hotkey_id: int) -> None:
    key = _linux_id_to_key.pop(hotkey_id, None)
    if key is None:
        return

    keycode, mod_mask = key
    _linux_registered.pop(key, None)

    root = _linux_display.screen().root
    for extra in _IGNORED_MODIFIER_COMBOS:
        root.ungrab_key(keycode, mod_mask | extra, root)
    _linux_display.sync()
