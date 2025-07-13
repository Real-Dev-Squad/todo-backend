from datetime import datetime
from pydantic import BaseModel
from .task_dto import TaskDTO


class WatchlistDTO(TaskDTO):
    watchlistId: str
    taskId: str


class CreateWatchlistDTO(BaseModel):
    taskId: str
    userId: str
    isActive: bool = True
    createdAt: datetime | None = None
    createdBy: str | None = None
    updatedAt: datetime | None = None
    updatedBy: str | None = None
