from bson import ObjectId
from pydantic import Field, validator
from typing import ClassVar
from datetime import datetime, timezone

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class TeamCreationInviteCodeModel(Document):
    """
    Model for team creation invite codes.
    """

    collection_name: ClassVar[str] = "team_creation_invite_codes"

    code: str = Field(..., min_length=6, max_length=20)
    description: str | None = None
    created_by: PyObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    used_at: datetime | None = None
    used_by: PyObjectId | None = None
    is_used: bool = False

    @validator("created_by", "used_by")
    def validate_object_id(cls, v):
        if v is None:
            return v
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return ObjectId(v)
