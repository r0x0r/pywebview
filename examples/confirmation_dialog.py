"""A window with a confirmation dialog."""

import webview


def open_confirmation_dialog(window):
    result = window.create_confirmation_dialog('Question', 'Are you ok with this?')
    if result:
        print('User clicked OK')
    else:
        print('User clicked Cancel')


if __name__ == '__main__':
    window = webview.create_window(
        'Confirmation dialog example', 'https://pywebview.flowrl.com/hello'
    )
    webview.start(open_confirmation_dialog, window)
