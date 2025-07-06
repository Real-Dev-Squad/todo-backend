from datetime import datetime
from pydantic import BaseModel

from todo.dto.user_dto import UserDTO


class LabelDTO(BaseModel):
    id: str
    name: str
    color: str
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    createdBy: UserDTO | None = None
    updatedBy: UserDTO | None = None
