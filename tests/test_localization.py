# -*- coding: utf-8 -*-
import webview
from .util import run_test


def test_localization():
    localization = {
        'cocoa.menu.about': u'О программе',
        'cocoa.menu.services': u'Cлужбы',
        'cocoa.menu.view': u'Вид',
        'cocoa.menu.hide': u'Скрыть',
        'cocoa.menu.hideOthers': u'Скрыть остальные',
        'cocoa.menu.showAll': u'Показать все',
        'cocoa.menu.quit': u'Завершить',
        'cocoa.menu.fullscreen': u'Полнж',
        'windows.fileFilter.allFiles': u'Все файлы',
        'windows.fileFilter.otherFiles': u'Остальлные файльы',
        'linux.openFile': u'Открыть файл',
        'linux.openFiles': u'Открыть файлы',
        'linux.openFolder': u'Открыть папку',
        'linux.saveFile': u'Сохранить файл',
    }

    window = webview.create_window('Localization test', 'https://www.example.org')
    run_test(webview, window, start_args={'localization': localization})






