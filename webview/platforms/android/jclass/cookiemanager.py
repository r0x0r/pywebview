from jnius import JavaClass, MetaJavaClass, JavaStaticMethod, JavaMethod, JavaMultipleMethod


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
