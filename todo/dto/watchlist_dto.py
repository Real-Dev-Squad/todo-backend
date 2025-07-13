from datetime import datetime
from pydantic import BaseModel, Field
from .task_dto import TaskDTO


class WatchlistDTO(TaskDTO):
    watchlistId: str
    taskId: str = Field(alias="id")


class CreateWatchlistDTO(BaseModel):
    taskId: str
    userId: str
    isActive: bool = True
    createdAt: datetime | None = None
    createdBy: str | None = None
    updatedAt: datetime | None = None
    updatedBy: str | None = None
