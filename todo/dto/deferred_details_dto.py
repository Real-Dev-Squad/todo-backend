from pydantic import BaseModel
from datetime import datetime
from todo.dto.user_dto import UserDTO


class DeferredDetailsDTO(BaseModel):
    deferredAt: datetime
    deferredTill: datetime
    deferredBy: UserDTO
