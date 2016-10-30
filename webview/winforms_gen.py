from ctypes import windll, c_int, c_uint
from ctypes.wintypes import BOOL, HWND, INT


SetWindowPos = windll.user32.SetWindowPos
SetWindowPos.restype = BOOL
SetWindowPos.argtypes = [
    HWND, #hWnd
    HWND, #hWndInsertAfter
    c_int,  #X
    c_int,  #Y
    c_int,  #cx
    c_int,  #cy
    c_uint, #uFlags
]

SetWindowPos = windll.user32.SetWindowPos
SetWindowPos.restype = BOOL
SetWindowPos.argtypes = [
    HWND, #hWnd
    HWND, #hWndInsertAfter
    c_int,  #X
    c_int,  #Y
    c_int,  #cx
    c_int,  #cy
    c_uint, #uFlags
]

GetSystemMetrics = windll.user32.GetSystemMetrics
GetSystemMetrics.restype = INT
GetSystemMetrics.argtypes = [
    INT
]