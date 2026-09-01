from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from webview.util import escape_string

if TYPE_CHECKING:
    from webview.dom.element import Element


class ClassList:
    def __init__(self, element: Element, classes: Iterable[str] | None = None) -> None:
        self.__element = element

        if classes:
            classes = escape_string(' '.join(classes))
            self.__element._window.evaluate_js(
                f"{self.__element._query_command}; element.className = '{classes}'"
            )

    def append(self, cls: str) -> None:
        self.__element._window.run_js(
            f"{self.__element._query_command}; element.classList.add('{escape_string(cls)}')"
        )

    def remove(self, cls: str) -> None:
        self.__element._window.run_js(
            f"{self.__element._query_command}; element.classList.remove('{escape_string(cls)}')"
        )

    def toggle(self, cls: str) -> None:
        self.__element._window.run_js(
            f"{self.__element._query_command}; element.classList.toggle('{escape_string(cls)}')"
        )

    def __get_classes(self) -> list[str]:
        classes = self.__element._window.evaluate_js(
            f'{self.__element._query_command}; element.className'
        ).split(' ')
        return [c for c in classes if c != '']

    def __getitem__(self, index: int) -> str:
        classes = self.__get_classes()
        return classes[index]

    def __len__(self) -> int:
        classes = self.__get_classes()
        return len(classes)

    def __str__(self) -> str:
        classes = self.__get_classes()
        return str(classes)

    def __repr__(self) -> str:
        classes = self.__get_classes()
        return repr(classes)

    def clear(self) -> None:
        self.__element._window.run_js(f"{self.__element._query_command}; element.className = ''")
