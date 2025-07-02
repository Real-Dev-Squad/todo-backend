from datetime import datetime
from typing import ClassVar

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class LabelModel(Document):
    collection_name: ClassVar[str] = "labels"

    name: str
    color: str
    isDeleted: bool = False
    createdAt: datetime
    updatedAt: datetime | None = None
    createdBy: str
    updatedBy: str | None = None
