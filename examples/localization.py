"""This example demonstrates how to localize GUI strings used by pywebview."""

import webview

if __name__ == "__main__":
    localization = {
        "global.saveFile": "Сохранить файл",
        "cocoa.menu.about": "О программе",
        "cocoa.menu.services": "Cлужбы",
        "cocoa.menu.view": "Вид",
        "cocoa.menu.hide": "Скрыть",
        "cocoa.menu.hideOthers": "Скрыть остальные",
        "cocoa.menu.showAll": "Показать все",
        "cocoa.menu.quit": "Завершить",
        "cocoa.menu.fullscreen": "Перейти ",
        "windows.fileFilter.allFiles": "Все файлы",
        "windows.fileFilter.otherFiles": "Остальлные файльы",
        "linux.openFile": "Открыть файл",
        "linux.openFiles": "Открыть файлы",
        "linux.openFolder": "Открыть папку",
    }

    window_localization_override = {
        "global.saveFile": "Save file",
    }

    webview.create_window(
        "Localization Example",
        "https://pywebview.flowrl.com/hello",
        localization=window_localization_override,
    )
    webview.start(localization=localization)
