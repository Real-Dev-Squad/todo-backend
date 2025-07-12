from pydantic import BaseModel
from datetime import datetime
from typing import List


class UserDTO(BaseModel):
    id: str
    name: str


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
