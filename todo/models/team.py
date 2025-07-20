from pydantic import Field
from typing import ClassVar, Optional
from datetime import datetime, timezone

from todo.models.common.document import Document


class TeamModel(Document):
    """
    Model for teams.
    """

    collection_name: ClassVar[str] = "teams"

    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    poc_id: str | None = None
    invite_code: str
    created_by: str
    updated_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False


class UserTeamDetailsModel(Document):
    """
    Model for user-team relationships.
    """

    collection_name: ClassVar[str] = "user_team_details"

    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    team_id: str
    is_active: bool = True
    role_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    updated_by: str
