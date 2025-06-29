from datetime import datetime
from typing import List
from pydantic import BaseModel, field_validator

from todo.constants.task import TaskPriority, TaskStatus
from todo.dto.deferred_details_dto import DeferredDetailsDTO
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
    deferredDetails: DeferredDetailsDTO | None = None
    createdAt: datetime
    updatedAt: datetime | None = None
    createdBy: UserDTO
    updatedBy: UserDTO | None = None

    class Config:
        json_encoders = {TaskPriority: lambda x: x.name}


class CreateTaskDTO(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.LOW
    status: TaskStatus = TaskStatus.TODO
    assignee: str | None = None
    labels: List[str] = []
    dueAt: datetime | None = None
    createdBy: str

    @field_validator("priority", mode="before")
    def parse_priority(cls, value):
        if isinstance(value, str):
            return TaskPriority[value]
        return value

    @field_validator("status", mode="before")
    def parse_status(cls, value):
        if isinstance(value, str):
            return TaskStatus[value]
        return value
