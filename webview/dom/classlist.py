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
        self.__class_list('add', cls)

    def remove(self, cls: str) -> None:
        self.__class_list('remove', cls)

    def toggle(self, cls: str) -> None:
        self.__class_list('toggle', cls)

    def __class_list(self, method: str, cls: str) -> None:
        self.__element._window.run_js(
            f"{self.__element._query_command}; element.classList.{method}('{escape_string(cls)}')"
        )

    def __get_classes(self) -> list[str]:
        return self.__element._window.evaluate_js(
            f'{self.__element._query_command}; Array.prototype.slice.call(element.classList)'
        )

    def __getitem__(self, index: int) -> str:
        return self.__get_classes()[index]

    def __len__(self) -> int:
        return len(self.__get_classes())

    def __str__(self) -> str:
        return str(self.__get_classes())

    def __repr__(self) -> str:
        return repr(self.__get_classes())

    def clear(self) -> None:
        self.__element._window.run_js(f"{self.__element._query_command}; element.className = ''")
