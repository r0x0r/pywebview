# Localization

Localize system text string used by pywebview. For a full list of used string, refer to the `webview/localization.py` file.

``` python
# -*- coding: utf-8 -*-

import webview


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

    webview.create_window('Localization Example', 'https://pywebview.flowrl.com/hello')
    webview.start(localization=localization)
```