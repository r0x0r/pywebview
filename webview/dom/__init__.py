from enum import Enum


class ManipulationMode(Enum):
    LastChild = 'LAST_CHILD'
    FirstChild = 'FIRST_CHILD'
    Before = 'BEFORE'
    After = 'AFTER'
    Replace = 'REPLACE'