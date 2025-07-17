from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class UserDTO(BaseModel):
    id: str
    name: str
    addedOn: Optional[datetime] = None
    tasksAssignedCount: Optional[int] = None


class UserSearchDTO(BaseModel):
    id: str
    name: str
    email_id: str
    created_at: datetime
    updated_at: datetime | None = None


class UserSearchResponseDTO(BaseModel):
    users: List[UserSearchDTO]
    total_count: int
    page: int
    limit: int
