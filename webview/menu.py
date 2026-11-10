from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

from webview.util import run_async


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
        self.function = function

        # Backends call the function synchronously in a thread, so run coroutines to completion
        if inspect.iscoroutinefunction(function):

            @wraps(function)
            def run_coroutine() -> Any:
                return run_async(function())

            self.function = run_coroutine
        # TODO: support platform-agnostic shortcut
        # self.shortcut = shortcut


class MenuSeparator:
    pass
