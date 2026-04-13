import ctypes
import logging as _logging
from ctypes import wintypes

_log = _logging.getLogger('pywebview')


_user32 = ctypes.windll.user32


# DEVMODE structure for EnumDisplaySettings
class DEVMODE(ctypes.Structure):
    _fields_ = [
        ('dmDeviceName', wintypes.WCHAR * 32),
        ('dmSpecVersion', wintypes.WORD),
        ('dmDriverVersion', wintypes.WORD),
        ('dmSize', wintypes.WORD),
        ('dmDriverExtra', wintypes.WORD),
        ('dmFields', wintypes.DWORD),
        ('dmPositionX', wintypes.LONG),
        ('dmPositionY', wintypes.LONG),
        ('dmDisplayOrientation', wintypes.DWORD),
        ('dmDisplayFixedOutput', wintypes.DWORD),
        ('dmColor', wintypes.SHORT),
        ('dmDuplex', wintypes.SHORT),
        ('dmYResolution', wintypes.SHORT),
        ('dmTTOption', wintypes.SHORT),
        ('dmCollate', wintypes.SHORT),
        ('dmFormName', wintypes.WCHAR * 32),
        ('dmLogPixels', wintypes.WORD),
        ('dmBitsPerPel', wintypes.DWORD),
        ('dmPelsWidth', wintypes.DWORD),
        ('dmPelsHeight', wintypes.DWORD),
        ('dmDisplayFlags', wintypes.DWORD),
        ('dmDisplayFrequency', wintypes.DWORD),
        ('dmICMMethod', wintypes.DWORD),
        ('dmICMIntent', wintypes.DWORD),
        ('dmMediaType', wintypes.DWORD),
        ('dmDitherType', wintypes.DWORD),
        ('dmReserved1', wintypes.DWORD),
        ('dmReserved2', wintypes.DWORD),
        ('dmPanningWidth', wintypes.DWORD),
        ('dmPanningHeight', wintypes.DWORD),
    ]


# DISPLAY_DEVICEW structure for EnumDisplayDevices
class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('DeviceName', wintypes.WCHAR * 32),
        ('DeviceString', wintypes.WCHAR * 128),
        ('StateFlags', wintypes.DWORD),
        ('DeviceID', wintypes.WCHAR * 128),
        ('DeviceKey', wintypes.WCHAR * 128),
    ]


def get_screen_scale(device_name: str, logical_width: int, logical_height: int) -> float:
    """
    Calculate the DPI scale factor for a screen.

    Args:
        device_name: The device name (e.g., "\\\\.\\DISPLAY1")
        logical_width: The logical width in pixels (DPI-scaled)
        logical_height: The logical height in pixels (DPI-scaled)

    Returns:
        The scale factor (e.g., 1.0, 1.5, 2.0, etc.)
    """
    try:
        dm = DEVMODE()
        dm.dmSize = ctypes.sizeof(DEVMODE)

        # ENUM_CURRENT_SETTINGS = -1
        if _user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
            physical_width = dm.dmPelsWidth
        else:
            # Fallback to logical size if EnumDisplaySettings fails
            return 1.0

        # Calculate scale from the ratio
        if logical_width > 0 and logical_height > 0:
            return physical_width / logical_width
        else:
            return 1.0

    except Exception as e:
        _log.debug(f'Failed to get display settings: {e}')
        return 1.0
