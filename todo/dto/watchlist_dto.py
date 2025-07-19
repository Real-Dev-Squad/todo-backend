from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from todo.constants.task import TaskPriority, TaskStatus


class AssigneeDTO(BaseModel):
    assignee_id: str
    assignee_name: str
    user_type: str  # "user" or "team"


class WatchlistDTO(BaseModel):
    taskId: str
    displayId: str
    title: str
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    isAcknowledged: Optional[bool] = None
    isDeleted: Optional[bool] = None
    labels: list = []
    dueAt: Optional[datetime] = None
    createdAt: datetime
    createdBy: str
    watchlistId: str
    assignee: Optional[AssigneeDTO] = None

    class Config:
        json_encoders = {TaskPriority: lambda x: x.name}


class CreateWatchlistDTO(BaseModel):
    taskId: str
    userId: str
    isActive: bool = True
    createdAt: datetime | None = None
    createdBy: str | None = None
    updatedAt: datetime | None = None
    updatedBy: str | None = None


class UpdateWatchlistDTO(BaseModel):
    isActive: bool
