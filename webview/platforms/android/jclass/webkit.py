from jnius import JavaClass, MetaJavaClass, JavaMethod, JavaStaticMethod, JavaMultipleMethod


class PyWebViewClient(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'com/pywebview/PyWebViewClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;Z)V')
    onPageFinished = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;)V')
    onReceivedSslError = JavaMethod('(Landroid/webkit/WebView;Landroid.webkit.SslErrorHandler;'
                                    'Landroid.net.http.SslError;)V')
    shouldInterceptRequest = JavaMethod('(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)'
                                        'Landroid.webkit.WebResourceResponse;')
    executeRequest = JavaMethod('(Ljava/lang/String;)Landroid.webkit.WebResourceResponse;')


class PyWebChromeClient(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'com/pywebview/PyWebChromeClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;)V')
    onJsAlert = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;Ljava/lang/String;'
                           'android.webkit.JsResult;)Z')
    onJsConfirm = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;Ljava/lang/String;'
                             'android.webkit.JsResult;)Z')


class PyJavascriptInterface(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'com/pywebview/PyJavascriptInterface'
    setCallback = JavaMethod('(Lcom/pywebview/JsApiCallbackWrapper;)V')
    call = JavaMethod('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')


class CookieManager(JavaClass, metaclass=MetaJavaClass):
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
