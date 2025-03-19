from enum import Enum


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
