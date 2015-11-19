from ctypes import *
from ctypes.wintypes import *

from comtypes import IUnknown, STDMETHOD, GUID, COMObject, COMMETHOD, wireHWND
from comtypes.automation import IDispatch

_WNDPROC = WINFUNCTYPE(c_long, c_int, c_uint, c_int, c_int)


class WNDCLASS(Structure):
    _fields_ = [('style', c_uint),
                ('lpfnWndProc', _WNDPROC),
                ('cbClsExtra', c_int),
                ('cbWndExtra', c_int),
                ('hInstance', c_int),
                ('hIcon', c_int),
                ('hCursor', c_int),
                ('hbrBackground', c_int),
                ('lpszMenuName', c_wchar_p),
                ('lpszClassName', c_wchar_p)]


class ICustomDoc(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{3050F3F0-98B5-11CF-BB82-00AA00BDCE0B}')
    _idlflags_ = []


class IDocHostUIHandler(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{BD3F23C0-D43E-11CF-893B-00AA00BDCE1A}')
    _idlflags_ = []


class _DOCHOSTUIINFO(Structure):
    pass


class IDropTarget(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{00000122-0000-0000-C000-000000000046}')
    _idlflags_ = []

class IDataObject(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{0000010E-0000-0000-C000-000000000046}')
    _idlflags_ = []

class IOleWindow(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{00000114-0000-0000-C000-000000000046}')
    _idlflags_ = []

class IOleInPlaceUIWindow(IOleWindow):
    _case_insensitive_ = True
    _iid_ = GUID('{00000115-0000-0000-C000-000000000046}')
    _idlflags_ = []
IOleWindow._methods_ = [
    COMMETHOD([], HRESULT, 'GetWindow',
              ( ['out'], POINTER(wireHWND), 'phwnd' )),
    COMMETHOD([], HRESULT, 'ContextSensitiveHelp',
              ( ['in'], c_int, 'fEnterMode' )),
]

class IOleInPlaceActiveObject(IOleWindow):
    _case_insensitive_ = True
    _iid_ = GUID('{00000117-0000-0000-C000-000000000046}')
    _idlflags_ = []

class IOleCommandTarget(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{B722BCCB-4E68-101B-A2BC-00AA00404770}')
    _idlflags_ = []

class IOleInPlaceFrame(IOleInPlaceUIWindow):
    _case_insensitive_ = True
    _iid_ = GUID('{00000116-0000-0000-C000-000000000046}')
    _idlflags_ = []

IOleInPlaceUIWindow._methods_ = [
    COMMETHOD([], HRESULT, 'GetBorder',
              ( ['out'], POINTER(tagRECT), 'lprectBorder' )),
    COMMETHOD([], HRESULT, 'RequestBorderSpace',
              ( ['in'], POINTER(tagRECT), 'pborderwidths' )),
    COMMETHOD([], HRESULT, 'SetBorderSpace',
              ( ['in'], POINTER(tagRECT), 'pborderwidths' )),
    COMMETHOD([], HRESULT, 'SetActiveObject',
              ( ['in'], POINTER(IOleInPlaceActiveObject), 'pActiveObject' ),
              ( ['in'], c_wchar_p, 'pszObjName' )),
]

IOleInPlaceActiveObject._methods_ = [
    COMMETHOD([], HRESULT, 'RemoteTranslateAccelerator'),
    COMMETHOD([], HRESULT, 'OnFrameWindowActivate',
              ( ['in'], c_int, 'fActivate' )),
    COMMETHOD([], HRESULT, 'OnDocWindowActivate',
              ( ['in'], c_int, 'fActivate' )),
    COMMETHOD([], HRESULT, 'RemoteResizeBorder',
              ( ['in'], POINTER(tagRECT), 'prcBorder' ),
              ( ['in'], POINTER(GUID), 'riid' ),
              ( ['in'], POINTER(IOleInPlaceUIWindow), 'pUIWindow' ),
              ( ['in'], c_int, 'fFrameWindow' )),
    COMMETHOD([], HRESULT, 'EnableModeless',
              ( ['in'], c_int, 'fEnable' )),
]

ICustomDoc._methods_ = [
    COMMETHOD([], HRESULT, 'SetUIHandler',
              ( ['in'], POINTER(IDocHostUIHandler), 'pUIHandler' )),
]

IDocHostUIHandler._methods_ = [
    COMMETHOD([], HRESULT, 'ShowContextMenu',
              ( ['in'], c_ulong, 'dwID' ),
              ( ['in'], POINTER(tagPOINT), 'ppt' ),
              ( ['in'], POINTER(IUnknown), 'pcmdtReserved' ),
              ( ['in'], POINTER(IDispatch), 'pdispReserved' )),
    COMMETHOD([], HRESULT, 'GetHostInfo',
              ( ['in'], POINTER(_DOCHOSTUIINFO), 'pInfo' )),
    COMMETHOD([], HRESULT, 'ShowUI',
              ( ['in'], c_ulong, 'dwID' ),
              ( ['in'], POINTER(IOleInPlaceActiveObject), 'pActiveObject' ),
              ( ['in'], POINTER(IOleCommandTarget), 'pCommandTarget' ),
              ( ['in'], POINTER(IOleInPlaceFrame), 'pFrame' ),
              ( ['in'], POINTER(IOleInPlaceUIWindow), 'pDoc' )),
    COMMETHOD([], HRESULT, 'HideUI'),
    COMMETHOD([], HRESULT, 'UpdateUI'),
    COMMETHOD([], HRESULT, 'EnableModeless',
              ( ['in'], c_int, 'fEnable' )),
    COMMETHOD([], HRESULT, 'OnDocWindowActivate',
              ( ['in'], c_int, 'fActivate' )),
    COMMETHOD([], HRESULT, 'OnFrameWindowActivate',
              ( ['in'], c_int, 'fActivate' )),
    COMMETHOD([], HRESULT, 'ResizeBorder',
              ( ['in'], POINTER(tagRECT), 'prcBorder' ),
              ( ['in'], POINTER(IOleInPlaceUIWindow), 'pUIWindow' ),
              ( ['in'], c_int, 'fRameWindow' )),
    COMMETHOD([], HRESULT, 'TranslateAccelerator',
              ( ['in'], POINTER(tagMSG), 'lpmsg' ),
              ( ['in'], POINTER(GUID), 'pguidCmdGroup' ),
              ( ['in'], c_ulong, 'nCmdID' )),
    COMMETHOD([], HRESULT, 'GetOptionKeyPath',
              ( ['out'], POINTER(c_wchar_p), 'pchKey' ),
              ( ['in'], c_ulong, 'dw' )),
    COMMETHOD([], HRESULT, 'GetDropTarget',
              ( ['in'], POINTER(IDropTarget), 'pDropTarget' ),
              ( ['out'], POINTER(POINTER(IDropTarget)), 'ppDropTarget' )),
    COMMETHOD([], HRESULT, 'GetExternal',
              ( ['out'], POINTER(POINTER(IDispatch)), 'ppDispatch' )),
    COMMETHOD([], HRESULT, 'TranslateUrl',
              ( ['in'], c_ulong, 'dwTranslate' ),
              ( ['in'], POINTER(c_ushort), 'pchURLIn' ),
              ( ['out'], POINTER(POINTER(c_ushort)), 'ppchURLOut' )),
    COMMETHOD([], HRESULT, 'FilterDataObject',
              ( ['in'], POINTER(IDataObject), 'pDO' ),
              ( ['out'], POINTER(POINTER(IDataObject)), 'ppDORet' )),
]

class MINMAXINFO(Structure):
    _fields_ = [
        ('ptReserved', POINT),
        ('ptMaxSize', POINT),
        ('ptMaxPosition', POINT),
        ('ptMinTrackSize', POINT),
        ('ptMaxTrackSize', POINT)
    ]
    __slots__ = [f[0] for f in _fields_]
