from typing import ClassVar
from datetime import datetime

from todo.models.common.document import Document


class WatchlistModel(Document):
    collection_name: ClassVar[str] = "watchlist"

    taskId: str
    userId: str
    isActive: bool = True
    createdAt: datetime
    createdBy: str
    updatedAt: datetime | None = None
    updatedBy: str | None = None
