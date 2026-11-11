from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from webview.util import call_maybe_async


class Menu:
    def __init__(
        self, title: str, items: list[Menu | MenuAction | MenuSeparator] | None = None
    ) -> None:
        """
        Args:
            title: the menu or submenu title
            items: the contents of the menu (can consist of Menu, MenuAction, or MenuSeparator instances)
        """
        self.title = title
        self.items = items if items is not None else []


class MenuAction:
    def __init__(self, title: str, function: Callable[[], Any]) -> None:
        self.title = title

        @wraps(function)
        def invoke() -> Any:
            return call_maybe_async(function)

        self.function = invoke
        # TODO: support platform-agnostic shortcut
        # self.shortcut = shortcut


class MenuSeparator:
    pass
