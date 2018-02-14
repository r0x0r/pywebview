# -*- coding: utf-8 -*-
import pytest
import threading
from .util import run_test, destroy_window


def localization():
    import webview

    def _localization(webview):
        assert webview.webview_ready(10)
        destroy_event.set()

    t = threading.Thread(target=_localization, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)

    strings = {
        "cocoa.menu.about": u"О программе",
        "cocoa.menu.services": u"Cлужбы",
        "cocoa.menu.view": u"Вид",
        "cocoa.menu.hide": u"Скрыть",
        "cocoa.menu.hideOthers": u"Скрыть остальные",
        "cocoa.menu.showAll": u"Показать все",
        "cocoa.menu.quit": u"Завершить",
        "cocoa.menu.fullscreen": u"Перейти ",
        "windows.fileFilter.allFiles": u"Все файлы",
        "windows.fileFilter.otherFiles": u"Остальлные файльы",
        "linux.openFile": u"Открыть файл",
        "linux.openFiles": u"Открыть файлы",
        "linux.openFolder": u"Открыть папку",
        "linux.saveFile": u"Сохранить файл",
    }

    webview.create_window('Localization test', 'https://www.example.org', strings=strings)


def test_localization():
    run_test(localization)
