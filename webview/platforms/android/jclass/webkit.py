__all__ = ('PyWebViewClient', 'PyWebChromeClient', 'PyJavascriptInterface', 'CookieManager', 'WebView')

from jnius import JavaClass, MetaJavaClass, JavaMethod, JavaStaticMethod, JavaMultipleMethod, JavaStaticField


class PyWebViewClient(JavaClass, metaclass=MetaJavaClass):
    """
    Represents a Java WebView client wrapper for interaction with Python.

    This class serves as a bridge between a Java WebView client in the Android
    platform and Python. It allows setting callbacks for events and intercepting
    requests, enabling Python code to handle Java WebView behaviors dynamically.

    Attributes:
        __javaclass__: str
            The fully qualified Java class name for the associated Java object.

    Methods:
        setCallback:
            Sets the callback wrapper to handle specific WebView events, along
            with an option to decide whether to enable or disable a specific
            callback mechanism.

        setRequestInterceptor:
            Sets a request interceptor to manage and modify WebView requests
            before they are processed.
    """
    __javaclass__ = 'com/pywebview/PyWebViewClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;Z)V')
    setRequestInterceptor = JavaMethod('(Lcom/pywebview/WebViewRequestInterceptor;)V')


class PyWebChromeClient(JavaClass, metaclass=MetaJavaClass):
    """
    Handles communication with the WebView's JavaScript environment.

    The PyWebChromeClient class acts as a bridge between JavaScript running in a WebView
    and the Python environment. By defining methods that handle JavaScript interactions,
    such as alert dialogs and confirmation dialogs, this class provides mechanisms
    to integrate JavaScript behaviors into Python-based applications.

    Attributes:
        __javaclass__: The fully qualified class name of the Java class that this Python
                       bridge wraps for interaction.

    Methods:
        setCallback: Sets the callback mechanism for handling JavaScript events. Takes an
                     EventCallbackWrapper as an argument.
        onJsAlert: Handles JavaScript alert dialogs presented within a WebView. It processes
                   the dialog content and determines whether the alert is handled in
                   the Python environment.
        onJsConfirm: Handles JavaScript confirmation dialogs within a WebView, allowing the
                     Python application to process the user's response to the dialog.
    """
    __javaclass__ = 'com/pywebview/PyWebChromeClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;)V')


class PyJavascriptInterface(JavaClass, metaclass=MetaJavaClass):
    """
    Interface that acts as a bridge between Python and the JavaScript context.

    This class provides methods to set a callback and to handle JavaScript
    calls by interfacing with the Java-based functionality. It enables
    interactions between Python code and JavaScript running on a web view or
    similar component by defining Java methods that can be invoked from
    JavaScript.

    Attributes:
        __javaclass__ (str): Represents the Java class path of the associated
            Java implementation.

    Methods:
        setCallback: Registers a JavaScript API callback wrapper to handle
            responses from JavaScript to Python.
        call: Executes a specified JavaScript function with provided context
            and arguments.
    """
    __javaclass__ = 'com/pywebview/PyJavascriptInterface'
    setCallback = JavaMethod('(Lcom/pywebview/JsApiCallbackWrapper;)V')
    call = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')


class CookieManager(JavaClass, metaclass=MetaJavaClass):
    """
    Manages browser cookies for the WebView component and provides methods for
    cookie handling.

    The CookieManager class offers a variety of methods to control HTTP cookie
    management within a WebView environment. Using this class, you can query,
    set, accept, and delete cookies, as well as enable or disable the acceptance
    of third-party or file-scheme cookies. Cookie management features are essential
    for maintaining session persistence and enforcing privacy policies in web views
    embedded within Android applications.

    Attributes:
        __javaclass__ (str): Specifies the underlying Java class representation
            of the `android.webkit.CookieManager`.

    Methods:
        getInstance(): Retrieves the singleton instance of the CookieManager.

        setAcceptCookie(accept: bool): Sets whether the WebView should accept
            cookies globally.

        acceptCookie(accept: bool): Checks whether the web environment accepts cookies.

        setAcceptThirdPartyCookies(view, accept: bool): Determines whether the
            specified WebView should accept third-party cookies.

        acceptThirdPartyCookies(view): Indicates whether the given WebView accepts
            third-party cookies.

        setCookie(url: str, value: str, callback: Optional = None): Sets a cookie
            for the specified URL, optionally performing an action asynchronously
            upon completion.

        getCookie(url: str): Retrieves the cookie(s) associated with the specified
            URL.

        removeSessionCookie(): Removes all session cookies synchronously.

        removeSessionCookies(callback): Removes all session cookies asynchronously,
            triggering the provided ValueCallback upon completion.

        removeAllCookie(): Deletes all cookies synchronously.

        removeAllCookies(callback): Deletes all cookies asynchronously, using the
            provided ValueCallback to notify when the task is completed.

        hasCookies(): Indicates whether any cookies are stored.

        removeExpiredCookie(): Removes cookies that are no longer valid based on
            their expiration attributes.

        flush(): Forces synchronous writing of the cookie state to storage.

        allowFileSchemeCookies(): Checks if cookies for file-scheme URLs are
            accepted.

        setAcceptFileSchemeCookies(accept: bool): Enables or disables the
            acceptance of cookies for file-scheme URLs.
    """
    __javaclass__ = 'android/webkit/CookieManager'

    getInstance = JavaStaticMethod('()Landroid/webkit/CookieManager;')
    setAcceptCookie = JavaMethod('(Z)V')
    acceptCookie = JavaMethod('(Z)V')
    setAcceptThirdPartyCookies = JavaMethod('(Landroid/webkit/WebView;Z)V')
    acceptThirdPartyCookies = JavaMethod('(Landroid/webkit/WebView;)Z')
    setCookie = JavaMultipleMethod([
        ('(Ljava/lang/String;Ljava/lang/String;)V', False, False),
        ('(Ljava/lang/String;Ljava/lang/String;Landroid/webkit/ValueCallback;)V', False, False)
    ])
    getCookie = JavaMethod('(Ljava/lang/String;)Ljava/lang/String;')
    removeSessionCookie = JavaMethod('()V')
    removeSessionCookies = JavaMethod('(Landroid/webkit/ValueCallback;)V')
    removeAllCookie = JavaMethod('()V')
    removeAllCookies = JavaMethod('(Landroid/webkit/ValueCallback;)V')
    hasCookies = JavaMethod('()Z')
    removeExpiredCookie = JavaMethod('()V')
    flush = JavaMethod('()V')
    allowFileSchemeCookies = JavaStaticMethod('()Z')
    setAcceptFileSchemeCookies = JavaStaticMethod('(Z)V')


class WebView(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'android/webkit/WebView'
    __javaconstructor__ = [
        ('(Landroid/content/Context;)V', False),
        ('(Landroid/content/Context;Landroid/util/AttributeSet;)V', False),
        ('(Landroid/content/Context;Landroid/util/AttributeSet;I)V', False),
        ('(Landroid/content/Context;Landroid/util/AttributeSet;II)V', False),
        ('(Landroid/content/Context;Landroid/util/AttributeSet;IZ)V', False)
    ]

    RENDERER_PRIORITY_BOUND = JavaStaticField('I')
    RENDERER_PRIORITY_IMPORTANT = JavaStaticField('I')
    RENDERER_PRIORITY_WAIVED = JavaStaticField('I')
    SCHEME_GEO = JavaStaticField('Ljava/lang/String;')
    SCHEME_MAILTO = JavaStaticField('Ljava/lang/String;')
    SCHEME_TEL = JavaStaticField('Ljava/lang/String;')

    setHorizontalScrollbarOverlay = JavaMethod('(Z)V')
    setVerticalScrollbarOverlay = JavaMethod('(Z)V')
    overlayHorizontalScrollbar = JavaMethod('()Z')
    overlayVerticalScrollbar = JavaMethod('()Z')
    getCertificate = JavaMethod('()Landroid/net/http/SslCertificate;')
    setCertificate = JavaMethod('(Landroid/net/http/SslCertificate;)V')
    savePassword = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
    setHttpAuthUsernamePassword = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
    getHttpAuthUsernamePassword = JavaMethod('(Ljava/lang/String;Ljava/lang/String;)[Ljava/lang/String;')
    destroy = JavaMethod('()V')
    setNetworkAvailable = JavaMethod('(Z)V')
    saveState = JavaMethod('(Landroid/os/Bundle;)Landroid/webkit/WebBackForwardList;')
    restoreState = JavaMethod('(Landroid/os/Bundle;)Landroid/webkit/WebBackForwardList;')

    loadUrl = JavaMultipleMethod([
        ('(Ljava/lang/String;)V', False, False),
        ('(Ljava/lang/String;Ljava/util/Map;)V', False, False)
    ])

    postUrl = JavaMethod('(Ljava/lang/String;[B)V')
    loadData = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
    loadDataWithBaseURL = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
    evaluateJavascript = JavaMethod('(Ljava/lang/String;Landroid/webkit/ValueCallback;)V')
    saveWebArchive = JavaMultipleMethod([
        ('(Ljava/lang/String;)V', False, False),
        ('(Ljava/lang/String;ZLandroid/webkit/ValueCallback;)V', False, False)
    ])
    stopLoading = JavaMethod('()V')
    reload = JavaMethod('()V')
    canGoBack = JavaMethod('()Z')
    goBack = JavaMethod('()V')
    canGoForward = JavaMethod('()Z')
    goForward = JavaMethod('()V')
    canGoBackOrForward = JavaMethod('(I)Z')
    goBackOrForward = JavaMethod('(I)V')
    isPrivateBrowsingEnabled = JavaMethod('()Z')
    pageUp = JavaMethod('(Z)Z')
    pageDown = JavaMethod('(Z)Z')
    postVisualStateCallback = JavaMethod('(JLandroid/webkit/WebView$VisualStateCallback;)V')
    clearView = JavaMethod('()V')
    capturePicture = JavaMethod('()Landroid/graphics/Picture;')
    createPrintDocumentAdapter = JavaMultipleMethod([
        ('()Landroid/print/PrintDocumentAdapter;', False, False),
        ('(Ljava/lang/String;)Landroid/print/PrintDocumentAdapter;', False, False)
    ])
    getScale = JavaMethod('()F')
    setInitialScale = JavaMethod('(I)V')
    invokeZoomPicker = JavaMethod('()V')
    getHitTestResult = JavaMethod('()Landroid/webkit/WebView$HitTestResult;')
    requestFocusNodeHref = JavaMethod('(Landroid/os/Message;)V')
    requestImageRef = JavaMethod('(Landroid/os/Message;)V')
    getUrl = JavaMethod('()Ljava/lang/String;')
    getOriginalUrl = JavaMethod('()Ljava/lang/String;')
    getTitle = JavaMethod('()Ljava/lang/String;')
    getFavicon = JavaMethod('()Landroid/graphics/Bitmap;')
    getProgress = JavaMethod('()I')
    getContentHeight = JavaMethod('()I')
    getHeight = JavaMethod('()I')
    getWidth = JavaMethod('()I')
    pauseTimers = JavaMethod('()V')
    resumeTimers = JavaMethod('()V')
    onPause = JavaMethod('()V')
    onResume = JavaMethod('()V')
    freeMemory = JavaMethod('()V')
    clearCache = JavaMethod('(Z)V')
    clearFormData = JavaMethod('()V')
    clearHistory = JavaMethod('()V')
    clearSslPreferences = JavaMethod('()V')
    clearClientCertPreferences = JavaStaticMethod('(Ljava/lang/Runnable;)V')
    startSafeBrowsing = JavaStaticMethod('(Landroid/content/Context;Landroid/webkit/ValueCallback;)V')
    setSafeBrowsingWhitelist = JavaStaticMethod('(Ljava/util/List;Landroid/webkit/ValueCallback;)V')
    getSafeBrowsingPrivacyPolicyUrl = JavaStaticMethod('()Landroid/net/Uri;')
    copyBackForwardList = JavaMethod('()Landroid/webkit/WebBackForwardList;')
    setFindListener = JavaMethod('(Landroid/webkit/WebView$FindListener;)V')
    findNext = JavaMethod('(Z)V')
    findAll = JavaMethod('(Ljava/lang/String;)I')
    findAllAsync = JavaMethod('(Ljava/lang/String;)V')
    showFindDialog = JavaMethod('(Ljava/lang/String;Z)Z')
    findAddress = JavaStaticMethod('(Ljava/lang/String;)Ljava/lang/String;')
    enableSlowWholeDocumentDraw = JavaStaticMethod('()V')

    clearMatches = JavaMethod('()V')
    documentHasImages = JavaMethod('(Landroid/os/Message;)V')
    setWebViewClient = JavaMethod('(Landroid/webkit/WebViewClient;)V')
    getWebViewClient = JavaMethod('()Landroid/webkit/WebViewClient;')
    getWebViewRenderProcess = JavaMethod('()Landroid/webkit/WebViewRenderProcess;')
    setWebViewRenderProcessClient_with_executor = JavaMethod(
        'Ljava/util/concurrent/Executor;Landroid/webkit/WebViewRenderProcessClient;V')
    setWebViewRenderProcessClient = JavaMultipleMethod([
        ('(Ljava/util/concurrent/Executor;Landroid/webkit/WebViewRenderProcessClient;)V', False, False),
        ('Landroid/webkit/WebViewRenderProcessClient;V', False, False),
    ])
    getWebViewRenderProcessClient = JavaMethod('()Landroid/webkit/WebViewRenderProcessClient;')
    setDownloadListener = JavaMethod('(Landroid/webkit/DownloadListener;)V')
    setWebChromeClient = JavaMethod('(Landroid/webkit/WebChromeClient;)V')
    getWebChromeClient = JavaMethod('()Landroid/webkit/WebChromeClient;')
    setPictureListener = JavaMethod('(Landroid/webkit/WebView$PictureListener;)V')
    setOnKeyListener = JavaMethod('(Landroid/view/View$OnKeyListener;)V')
    addJavascriptInterface = JavaMethod('(Ljava/lang/Object;Ljava/lang/String;)V')
    removeJavascriptInterface = JavaMethod('(Ljava/lang/String;)V')
    createWebMessageChannel = JavaMethod('()[Landroid/webkit/WebMessagePort;')
    postWebMessage = JavaMethod('(Landroid/webkit/WebMessage;Landroid/net/Uri;)V')
    getSettings = JavaMethod('()Landroid/webkit/WebSettings;')
    setWebContentsDebuggingEnabled = JavaStaticMethod('(Z)V')
    setDataDirectorySuffix = JavaStaticMethod('(Ljava/lang/String;)V')
    disableWebView = JavaStaticMethod('()V')
    onChildViewAdded = JavaMethod('(Landroid/view/View;Landroid/view/View;)V')
    onChildViewRemoved = JavaMethod('(Landroid/view/View;Landroid/view/View;)V')
    onGlobalFocusChanged = JavaMethod('(Landroid/view/View;Landroid/view/View;)V')
    setMapTrackballToArrowKeys = JavaMethod('(Z)V')
    flingScroll = JavaMethod('(II)V')
    canZoomIn = JavaMethod('()Z')
    canZoomOut = JavaMethod('()Z')
    zoomBy = JavaMethod('(F)V')
    zoomIn = JavaMethod('()Z')
    zoomOut = JavaMethod('()Z')
    setRendererPriorityPolicy = JavaMethod('(IZ)V')
    getRendererRequestedPriority = JavaMethod('()I')
    getRendererPriorityWaivedWhenNotVisible = JavaMethod('()Z')
    setTextClassifier = JavaMethod('(Landroid/view/textclassifier/TextClassifier;)V')
    getTextClassifier = JavaMethod('()Landroid/view/textclassifier/TextClassifier;')
    getWebViewClassLoader = JavaStaticMethod('()Ljava/lang/ClassLoader;')
    getWebViewLooper = JavaMethod('()Landroid/os/Looper;')
    onAttachedToWindow = JavaMethod('()V')
    setLayoutParams = JavaMethod('(Landroid/view/ViewGroup$LayoutParams;)V')
    setOverScrollMode = JavaMethod('(I)V')
    setScrollBarStyle = JavaMethod('(I)V')
    computeScroll = JavaMethod('()V')
    onHoverEvent = JavaMethod('(Landroid/view/MotionEvent;)Z')
    onTouchEvent = JavaMethod('(Landroid/view/MotionEvent;)Z')
    onGenericMotionEvent = JavaMethod('(Landroid/view/MotionEvent;)Z')
    onTrackballEvent = JavaMethod('(Landroid/view/MotionEvent;)Z')
    onKeyDown = JavaMethod('(ILandroid/view/KeyEvent;)Z')
    onKeyUp = JavaMethod('(ILandroid/view/KeyEvent;)Z')
    onKeyMultiple = JavaMethod('(IILandroid/view/KeyEvent;)Z')
    getAccessibilityNodeProvider = JavaMethod('()Landroid/view/accessibility/AccessibilityNodeProvider;')
    shouldDelayChildPressedState = JavaMethod('()Z')
    getAccessibilityClassName = JavaMethod('()Ljava/lang/CharSequence;')
    onProvideVirtualStructure = JavaMethod('(Landroid/view/ViewStructure;)V')
    onProvideAutofillVirtualStructure = JavaMethod('(Landroid/view/ViewStructure;I)V')
    onProvideContentCaptureStructure = JavaMethod('(Landroid/view/ViewStructure;I)V')
    autofill = JavaMethod('(Landroid/util/SparseArray;)V')
    isVisibleToUserForAutofill = JavaMethod('(I)Z')
    onCreateVirtualViewTranslationRequests = JavaMethod('([J[ILjava/util/function/Consumer;)V')
    dispatchCreateViewTranslationRequest = JavaMethod(
        '(Ljava/util/Map;[ILandroid/view/translation/TranslationCapability;Ljava/util/List;)V')
    onVirtualViewTranslationResponses = JavaMethod('(Landroid/util/LongSparseArray;)V')
    onOverScrolled = JavaMethod('(IIZZ)V')
    onWindowVisibilityChanged = JavaMethod('(I)V')
    onDraw = JavaMethod('(Landroid/graphics/Canvas;)V')
    performLongClick = JavaMethod('()Z')
    onConfigurationChanged = JavaMethod('(Landroid/content/res/Configuration;)V')
    onCreateInputConnection = JavaMethod('(Landroid/view/inputmethod/EditorInfo;)'
                                         'Landroid/view/inputmethod/InputConnection;')
    onDragEvent = JavaMethod('(Landroid/view/DragEvent;)Z')
    onVisibilityChanged = JavaMethod('(Landroid/view/View;I)V')
    onWindowFocusChanged = JavaMethod('(Z)V')
    onFocusChanged = JavaMethod('(ZILandroid/graphics/Rect;)V')
    onSizeChanged = JavaMethod('(IIII)V')
    onScrollChanged = JavaMethod('(IIII)V')
    dispatchKeyEvent = JavaMethod('(Landroid/view/KeyEvent;)Z')
    requestFocus = JavaMethod('(ILandroid/graphics/Rect;)Z')
    onMeasure = JavaMethod('(II)V')
    requestChildRectangleOnScreen = JavaMethod('(Landroid/view/View;Landroid/graphics/Rect;Z)Z')
    setBackgroundColor = JavaMethod('(I)V')
    setLayerType = JavaMethod('(ILandroid/graphics/Paint;)V')
    dispatchDraw = JavaMethod('(Landroid/graphics/Canvas;)V')
    onStartTemporaryDetach = JavaMethod('()V')
    onFinishTemporaryDetach = JavaMethod('()V')
    getHandler = JavaMethod('()Landroid/os/Handler;')
    findFocus = JavaMethod('()Landroid/view/View;')
    getCurrentWebViewPackage = JavaStaticMethod('()Landroid/content/pm/PackageInfo;')
    onCheckIsTextEditor = JavaMethod('()Z')
    onApplyWindowInsets = JavaMethod('(Landroid/view/WindowInsets;)Landroid/view/WindowInsets;')
    onResolvePointerIcon = JavaMethod('(Landroid/view/MotionEvent;I)Landroid/view/PointerIcon;')


