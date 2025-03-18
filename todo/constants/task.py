from enum import Enum

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 200

class TaskStatus(Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    DONE = "DONE"


class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3
