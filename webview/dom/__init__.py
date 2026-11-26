from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ManipulationMode(Enum):
    LastChild = 'LAST_CHILD'
    FirstChild = 'FIRST_CHILD'
    Before = 'BEFORE'
    After = 'AFTER'
    Replace = 'REPLACE'


@dataclass(frozen=True, eq=False)
class DOMEventHandler:
    callback: Callable
    prevent_default: bool = False
    stop_propagation: bool = False
    stop_immediate_propagation: bool = False
    debounce: int = 0


_dnd_state: dict[str, Any] = {'num_listeners': 0, 'paths': [], 'dropped': None}
