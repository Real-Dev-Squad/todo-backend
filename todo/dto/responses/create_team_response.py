from pydantic import BaseModel
from todo.dto.team_dto import TeamDTO


class CreateTeamResponse(BaseModel):
    team: TeamDTO
    message: str
