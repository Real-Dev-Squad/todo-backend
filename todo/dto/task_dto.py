from datetime import datetime
from typing import List
from pydantic import BaseModel

from todo.constants.task import TaskPriority, TaskStatus
from todo.dto.label_dto import LabelDTO
from todo.dto.user_dto import UserDTO


class TaskDTO(BaseModel):
    id: str
    displayId: str
    title: str
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assignee: UserDTO | None = None
    isAcknowledged: bool | None = None
    labels: List[LabelDTO] = []
    startedAt: datetime | None = None
    dueAt: datetime | None = None
    createdAt: datetime
    updatedAt: datetime | None = None
    createdBy: UserDTO
    updatedBy: UserDTO | None = None

    class Config:
        json_encoders = {TaskPriority: lambda x: x.name}
