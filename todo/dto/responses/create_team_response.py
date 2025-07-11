from pydantic import BaseModel
from todo.dto.team_dto import TeamDTO


class CreateTeamResponse(BaseModel):
    """Response model for team creation endpoint.

    Attributes:
        team: The newly created team details
        message: Success or status message from the operation
    """

    team: TeamDTO
    message: str
