from jnius import JavaClass, MetaJavaClass, JavaMethod


class PyWebViewClient(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'com/pywebview/PyWebViewClient'
    setCallback = JavaMethod('(Lcom/pywebview/EventCallbackWrapper;Z)V')
    onPageFinished = JavaMethod('(Landroid/webkit/WebView;Ljava/lang/String;)V')
    onReceivedSslError = JavaMethod('(Landroid/webkit/WebView;Landroid.webkit.SslErrorHandler;'
                                    'Landroid.net.http.SslError;)V')
    shouldInterceptRequest = JavaMethod('(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)'
                                        'Landroid.webkit.WebResourceResponse;')
    executeRequest = JavaMethod('(Ljava/lang/String;)Landroid.webkit.WebResourceResponse;')
