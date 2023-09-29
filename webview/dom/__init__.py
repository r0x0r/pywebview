from enum import Enum
from typing import Callable


class ManipulationMode(Enum):
    LastChild = 'LAST_CHILD'
    FirstChild = 'FIRST_CHILD'
    Before = 'BEFORE'
    After = 'AFTER'
    Replace = 'REPLACE'


class DOMEventHandler:
    def __init__(self, callback: Callable, prevent_default: bool=False, stop_propagation: bool=False, stop_immediate_propagation: bool=False):
        self.__callback = callback
        self.__prevent_default = prevent_default
        self.__stop_propagation = stop_propagation
        self.__stop_immediate_propagation = stop_immediate_propagation

    @property
    def callback(self):
        return self.__callback

    @property
    def prevent_default(self):
        return self.__prevent_default

    @property
    def stop_propagation(self):
        return self.__stop_propagation

    @property
    def stop_immediate_propagation(self):
        return self.__stop_immediate_propagation


_dnd_state = {
    'num_listeners': 0,
    'paths': []
}
