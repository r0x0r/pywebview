# -*- coding: utf-8 -*-

import webview

"""
This example demonstrates how to localize GUI strings used by pywebview.
"""

if __name__ == '__main__':
    localization = {
        'global.saveFile': u'Сохранить файл',
        'cocoa.menu.about': u'О программе',
        'cocoa.menu.services': u'Cлужбы',
        'cocoa.menu.view': u'Вид',
        'cocoa.menu.hide': u'Скрыть',
        'cocoa.menu.hideOthers': u'Скрыть остальные',
        'cocoa.menu.showAll': u'Показать все',
        'cocoa.menu.quit': u'Завершить',
        'cocoa.menu.fullscreen': u'Перейти ',
        'windows.fileFilter.allFiles': u'Все файлы',
        'windows.fileFilter.otherFiles': u'Остальлные файльы',
        'linux.openFile': u'Открыть файл',
        'linux.openFiles': u'Открыть файлы',
        'linux.openFolder': u'Открыть папку',
    }

    window_localization_override = {
        'global.saveFile': u'Save file',
    }

    webview.create_window(
        'Localization Example',
        'https://pywebview.flowrl.com/hello',
        localization=window_localization_override,
    )
    webview.start(localization=localization)
