__all__ = ('AlertDialogBuilder', 'DownloadManagerRequest')

from jnius import JavaClass, MetaJavaClass, JavaMultipleMethod, JavaMethod, JavaStaticField


class AlertDialogBuilder(JavaClass, metaclass=MetaJavaClass):
    """
    Represents a builder for creating AlertDialog instances in the Android platform.

    This class provides a fluent API for constructing and customizing AlertDialog instances
    with various settings such as title, message, icon, buttons, custom views, and other
    behavioral options. It serves as a wrapper around the native Java AlertDialog.Builder
    implementation, enabling its usage within Python applications interfacing with Android.

    Attributes:
        __javaclass__ (str): Specifies the Java class represented by this Python class.
        __javaconstructor__ (list): Defines available constructors in the underlying Java class.

    Methods:
        setTitle: Sets the title of the AlertDialog.
        setCustomTitle: Sets a custom view to be used as the title of the AlertDialog.
        setMessage: Specifies the message text for the AlertDialog.
        setIcon: Sets the icon for the AlertDialog.
        setIconAttribute: Sets an attribute as the icon for the AlertDialog.
        setPositiveButton: Sets positive button text and its click listener.
        setNegativeButton: Sets negative button text and its click listener.
        setNeutralButton: Sets neutral button text and its click listener.
        setCancelable: Configures whether the AlertDialog is cancelable or not.
        setOnCancelListener: Sets the cancel listener to invoke when the AlertDialog is canceled.
        setOnDismissListener: Sets a listener for when the AlertDialog is dismissed.
        setOnKeyListener: Sets a key listener for key events within the AlertDialog.
        setItems: Populates the AlertDialog with a list of selectable items.
        setAdapter: Populates the AlertDialog with a list using a custom adapter.
        setCursor: Sets a cursor to define the data to be displayed in the AlertDialog.
        setMultiChoiceItems: Configures multiple choice items and their states for the AlertDialog.
        setSingleChoiceItems: Configures single-choice items and their states for the AlertDialog.
        setView: Sets a custom view to be displayed in the AlertDialog.
        setInverseBackgroundForced: Specifies whether to force the AlertDialog to use an inverse background.
        create: Constructs an AlertDialog instance without displaying it.
        show: Shows the AlertDialog after construction.
    """
    __javaclass__ = 'android/app/AlertDialog$Builder'
    __javaconstructor__ = [
        ('(Landroid/content/Context;)V', False),
        ('(Landroid/content/Context;I)V', False)
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


class DownloadManagerRequest(JavaClass, metaclass=MetaJavaClass):
    """
    Represents a request for downloading a file, providing methods to configure
    download behavior and properties. This class is a part of the Android Download
    Manager system, enabling developers to easily handle file downloads in
    background.

    The DownloadManagerRequest class allows setting various options for a download
    request, including destination, network restrictions, visibility, and more. It is
    designed to be used as a configuration object passed to the DownloadManager
    to initiate a download task.

    Attributes:
        NETWORK_MOBILE: int
            Specifies that downloads are allowed over a mobile network connection.
        NETWORK_WIFI: int
            Specifies that downloads are allowed over a Wi-Fi network connection.
        VISIBILITY_HIDDEN: int
            Visibility state where the download is hidden from the user interface.
        VISIBILITY_VISIBLE: int
            Visibility state where the download is visible in the user interface.
        VISIBILITY_VISIBLE_NOTIFY_COMPLETED: int
            Visibility state where the download's completion will notify the user.
        VISIBILITY_VISIBLE_NOTIFY_ONLY_COMPLETION: int
            Visibility state where only completion of the download notifies the user.
    """
    __javaclass__ = 'android/app/DownloadManager$Request'
    __javaconstructor__ = [
        ('(Landroid/net/Uri;)V', False)
    ]
    NETWORK_MOBILE = JavaStaticField('I')
    NETWORK_WIFI = JavaStaticField('I')
    VISIBILITY_HIDDEN = JavaStaticField('I')
    VISIBILITY_VISIBLE = JavaStaticField('I')
    VISIBILITY_VISIBLE_NOTIFY_COMPLETED = JavaStaticField('I')
    VISIBILITY_VISIBLE_NOTIFY_ONLY_COMPLETION = JavaStaticField('I')
    setDestinationUri = JavaMethod('(Landroid/net/Uri;)Landroid/app/DownloadManager$Request;')
    setDestinationInExternalFilesDir = JavaMethod('(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;)'
                                                  'Landroid/app/DownloadManager$Request;')
    setDestinationInExternalPublicDir = JavaMethod('(Ljava/lang/String;Ljava/lang/String;)'
                                                   'Landroid/app/DownloadManager$Request;')
    allowScanningByMediaScanner = JavaMethod('()V')
    addRequestHeader = JavaMethod('(Ljava/lang/String;Ljava/lang/String;)Landroid/app/DownloadManager$Request;')
    setTitle = JavaMethod('(Ljava/lang/CharSequence;)Landroid/app/DownloadManager$Request;')
    setDescription = JavaMethod('(Ljava/lang/CharSequence;)Landroid/app/DownloadManager$Request;')
    setMimeType = JavaMethod('(Ljava/lang/String;)Landroid/app/DownloadManager$Request;')
    setShowRunningNotification = JavaMethod('(Z)Landroid/app/DownloadManager$Request;')
    setNotificationVisibility = JavaMethod('(I)Landroid/app/DownloadManager$Request;')
    setAllowedNetworkTypes = JavaMethod('(I)Landroid/app/DownloadManager$Request;')
    setAllowedOverRoaming = JavaMethod('(Z)Landroid/app/DownloadManager$Request;')
    setAllowedOverMetered = JavaMethod('(Z)Landroid/app/DownloadManager$Request;')
    setRequiresDeviceIdle = JavaMethod('(Z)Landroid/app/DownloadManager$Request;')
    setRequiresCharging = JavaMethod('(Z)Landroid/app/DownloadManager$Request;')
    setVisibleInDownloadsUi = JavaMethod('(Z)Landroid/app/DownloadManager$Request;')

