from pydantic import BaseModel, Field
from typing import List


class AddTeamMemberDTO(BaseModel):
    member_ids: List[str] = Field(..., description="List of user IDs to add to the team")
