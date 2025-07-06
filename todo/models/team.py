from pydantic import Field
from typing import ClassVar
from datetime import datetime, timezone

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class TeamModel(Document):
    """
    Model for teams.
    """

    collection_name: ClassVar[str] = "teams"

    name: str
    description: str | None = None
    poc_id: PyObjectId
    created_by: PyObjectId
    updated_by: PyObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False


class UserTeamDetailsModel(Document):
    """
    Model for user-team relationships.
    """

    collection_name: ClassVar[str] = "userTeamDetails"

    user_id: PyObjectId
    team_id: PyObjectId
    is_active: bool = True
    role_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: PyObjectId
    updated_by: PyObjectId
