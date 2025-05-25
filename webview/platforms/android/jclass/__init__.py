"""
This package will help reduce overhead startup time of pywebview android application
on android. It will be responsible for defining android and api signature to reduce
the over head cost of pyjnius finding all signatures by itself.
"""

from jnius import JavaClass, MetaJavaClass, JavaMethod, JavaMultipleMethod, JavaStaticMethod


class AlertDialogBuilder(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'android/app/AlertDialog$Builder'
    __javaconstructor__ = [
        ('(Landroid/content/Context;)V', False),
        ('()Landroid/content/Context;', False)
    ]
    setTitle = JavaMultipleMethod([
        ('(I)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setCustomTitle = JavaMethod('(Landroid/view/View;)Landroid/app/AlertDialog$Builder;')
    setMessage = JavaMultipleMethod([
        ('(I)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setIcon = JavaMultipleMethod([
        ('(I)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Landroid/graphics/drawable/Drawable;)Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setIconAttribute = JavaMethod('(I)Landroid/app/AlertDialog$Builder;')
    setPositiveButton = JavaMultipleMethod([
        ('(ILandroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setNegativeButton = JavaMultipleMethod([
        ('(ILandroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setNeutralButton = JavaMultipleMethod([
        ('(ILandroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setCancelable = JavaMethod('(Z)Landroid/app/AlertDialog$Builder;')
    setOnCancelListener = JavaMethod('(Landroid/content/DialogInterface$OnCancelListener;)'
                                     'Landroid/app/AlertDialog$Builder;')
    setOnDismissListener = JavaMethod('(Landroid/content/DialogInterface$OnDismissListener;)'
                                      'Landroid/app/AlertDialog$Builder;')
    setOnKeyListener = JavaMethod('(Landroid/content/DialogInterface$OnKeyListener;)'
                                  'Landroid/app/AlertDialog$Builder;')
    setItems = JavaMultipleMethod([
        ('(ILandroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;', False, False),
        ('([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setAdapter = JavaMethod('(Landroid/widget/ListAdapter;Landroid/content/DialogInterface$OnClickListener;)'
                            'Landroid/app/AlertDialog$Builder;')
    setCursor = JavaMethod('(Landroid/database/Cursor;Landroid/content/DialogInterface$OnClickListener;'
                           'Ljava/lang/String;)Landroid/app/AlertDialog$Builder;')
    setMultiChoiceItems = JavaMultipleMethod([
        ('(I[ZLandroid/content/DialogInterface$OnMultiChoiceClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False),
        ('([Ljava/lang/CharSequence;[ZLandroid/content/DialogInterface$OnMultiChoiceClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False),
        ('(Landroid/database/Cursor;Ljava/lang/String;'
         'Ljava/lang/String;Landroid/content/DialogInterface$OnMultiChoiceClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setSingleChoiceItems = JavaMultipleMethod([
        ('(IILandroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Landroid/database/Cursor;ILjava/lang/String;Landroid/content/DialogInterface$OnClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False),
        ('([Ljava/lang/CharSequence;ILandroid/content/DialogInterface$OnClickListener;)'
         'Landroid/app/AlertDialog$Builder;', False, False),
        ('(Landroid/widget/ListAdapter;ILandroid/content/DialogInterface$OnClickListener;)', False, False)
    ])
    setView = JavaMultipleMethod([
        ('(I)Landroid/app/AlertDialog$Builder;', False, False),
        ('(Landroid/view/View;)Landroid/app/AlertDialog$Builder;', False, False)
    ])
    setInverseBackgroundForced = JavaMethod('(Z)Landroid/app/AlertDialog$Builder;')
    create = JavaMethod('()Landroid/app/AlertDialog;')
    show = JavaMethod('()Landroid/app/AlertDialog;')


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
