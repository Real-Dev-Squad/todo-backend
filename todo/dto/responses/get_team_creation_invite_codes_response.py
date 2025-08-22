from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TeamCreationInviteCodeListItemDTO(BaseModel):
    """DTO for a single team creation invite code in the list."""

    id: str = Field(description="Unique identifier for the team creation invite code")
    code: str = Field(description="The actual invite code")
    description: Optional[str] = Field(None, description="Optional description provided when generating the code")
    created_by: dict = Field(description="User details of who created this code")
    created_at: datetime = Field(description="Timestamp when the code was created")
    used_at: Optional[datetime] = Field(None, description="Timestamp when the code was used (null if unused)")
    used_by: Optional[dict] = Field(None, description="User details of who used this code (null if unused)")
    is_used: bool = Field(description="Whether this code has been used for team creation")


class GetTeamCreationInviteCodesResponse(BaseModel):
    """Response model for listing all team creation invite codes with pagination links."""

    codes: List[TeamCreationInviteCodeListItemDTO] = Field(
        description="List of team creation invite codes for current page"
    )
    previous_url: Optional[str] = Field(None, description="URL for previous page (null if no previous page)")
    next_url: Optional[str] = Field(None, description="URL for next page (null if no next page)")
    message: str = Field(description="Success message")
