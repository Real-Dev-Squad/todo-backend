from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class WatchlistDTO(BaseModel):
    taskId: str
    displayId: str
    title: str
    description: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    isAcknowledged: Optional[bool] = None
    isDeleted: Optional[bool] = None
    labels: list = []
    dueAt: Optional[datetime] = None
    createdAt: datetime
    createdBy: str
    watchlistId: str


class CreateWatchlistDTO(BaseModel):
    taskId: str
    userId: str
    isActive: bool = True
    createdAt: datetime | None = None
    createdBy: str | None = None
    updatedAt: datetime | None = None
    updatedBy: str | None = None
