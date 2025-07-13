from typing import List
from pydantic import BaseModel
from todo.dto.team_dto import TeamDTO


class GetUserTeamsResponse(BaseModel):
    teams: List[TeamDTO] = []
    total: int = 0 