from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CreateTeamDTO(BaseModel):
    name: str
    description: Optional[str] = None
    member_ids: List[str] = []
    poc_id: str


class TeamDTO(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    poc_id: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
