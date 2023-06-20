import webview

from .util import run_test


def test_localization():
    localization = {
        'cocoa.menu.about': 'О программе',
        'cocoa.menu.services': 'Cлужбы',
        'cocoa.menu.view': 'Вид',
        'cocoa.menu.hide': 'Скрыть',
        'cocoa.menu.hideOthers': 'Скрыть остальные',
        'cocoa.menu.showAll': 'Показать все',
        'cocoa.menu.quit': 'Завершить',
        'cocoa.menu.fullscreen': 'Полнж',
        'windows.fileFilter.allFiles': 'Все файлы',
        'windows.fileFilter.otherFiles': 'Остальлные файльы',
        'linux.openFile': 'Открыть файл',
        'linux.openFiles': 'Открыть файлы',
        'linux.openFolder': 'Открыть папку',
        'linux.saveFile': 'Сохранить файл',
    }

    window = webview.create_window('Localization test', 'https://www.example.org')
    run_test(webview, window, start_args={'localization': localization})
