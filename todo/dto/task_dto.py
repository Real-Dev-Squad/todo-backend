from datetime import datetime
from typing import List
from bson import ObjectId
from pydantic import BaseModel, field_validator

from todo.constants.messages import ValidationErrors
from todo.constants.task import TaskPriority, TaskStatus
from todo.dto.deferred_details_dto import DeferredDetailsDTO
from todo.dto.label_dto import LabelDTO
from todo.dto.user_dto import UserDTO
from todo.dto.assignee_task_details_dto import AssigneeInfoDTO


class TaskDTO(BaseModel):
    id: str
    displayId: str
    title: str
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assignee: AssigneeInfoDTO | None = None
    isAcknowledged: bool | None = None
    labels: List[LabelDTO] = []
    startedAt: datetime | None = None
    dueAt: datetime | None = None
    deferredDetails: DeferredDetailsDTO | None = None
    in_watchlist: bool = False
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
    assignee: dict | None = None  # {"assignee_id": str, "relation_type": "team"|"user"}
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

    @field_validator("createdBy")
    def validate_created_by(cls, value: str) -> str:
        if not ObjectId.is_valid(value):
            raise ValueError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value
