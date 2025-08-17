from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GenerateTeamCreationInviteCodeDTO(BaseModel):
    """DTO for generating team creation invite codes."""

    description: Optional[str] = None


class VerifyTeamCreationInviteCodeDTO(BaseModel):
    """DTO for verifying team creation invite codes."""

    code: str


class TeamCreationInviteCodeDTO(BaseModel):
    """DTO for team creation invite code data."""

    id: str = Field(description="Unique identifier for the team invite code")
    code: str = Field(description="The actual invite code (6-20 characters)")
    description: Optional[str] = Field(None, description="Optional description provided when generating the code")
    created_by: str = Field(description="User ID of the admin who generated this code")
    created_at: datetime = Field(description="Timestamp when the code was created")
    used_at: Optional[datetime] = Field(None, description="Timestamp when the code was used (null if unused)")
    used_by: Optional[str] = Field(None, description="User ID who used this code (null if unused)")
    is_used: bool = Field(description="Whether this code has been used for team creation")
