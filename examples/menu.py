"""Create an application menu."""

import webview
from webview.menu import Menu, MenuAction, MenuSeparator


def change_active_window_content():
    active_window = webview.active_window()
    if active_window:
        active_window.load_html('<h1>You changed this window!</h1>')


def click_me():
    active_window = webview.active_window()
    if active_window:
        active_window.load_html('<h1>You clicked me!</h1>')


def test():
    active_window = webview.active_window()
    if active_window:
        active_window.load_html('<h1>This is a test!</h1>')

def do_nothing():
    pass


def say_this_is_window_2():
    active_window = webview.active_window()
    if active_window:
        active_window.load_html('<h1>This is window 2</h2>')


def open_save_file_dialog():
    active_window = webview.active_window()
    active_window.create_file_dialog(webview.FileDialog.SAVE, directory='/', save_filename='test.file')


def open_preferences():
    active_window = webview.active_window()
    if active_window:
        active_window.load_html('<h1>Preferences</h1><p>App preferences would open here (macOS app menu)</p>')


def check_for_updates():
    active_window = webview.active_window()
    if active_window:
        active_window.load_html('<h1>Check for Updates</h1><p>Checking for updates... (macOS app menu)</p>')


if __name__ == '__main__':
    # App menu items (macOS only - appears between About and Services)
    # On other platforms, this menu is ignored
    macos_app_menu = Menu('__app__', [
        MenuAction('Preferences...', open_preferences),
        MenuSeparator(),
        MenuAction('Check for Updates', check_for_updates),
    ])

    window_menu = [Menu(
        'Window', [
            MenuAction('Test', test)
        ]
    )]

    app_menu = [
        macos_app_menu,  # macOS app menu items
        Menu(
            'Menu 1',
            [
                MenuAction('Change Active Window Content', change_active_window_content),
                MenuSeparator(),
                Menu(
                    'Random',
                    [
                        MenuAction('Click Me', click_me),
                        MenuAction('File Dialog', open_save_file_dialog),
                    ],
                ),
            ],
        ),
        Menu('Menu 2', [MenuAction('This will do nothing', do_nothing)]),
    ]


    window_1 = webview.create_window(
        'Application Menu Example', 'https://pywebview.flowrl.com/hello'
    )
    window_2 = webview.create_window(
        'Window Menu Example', html='<h1>Another window to test application menu</h1>', menu=window_menu
    )

    webview.start(menu=app_menu)
