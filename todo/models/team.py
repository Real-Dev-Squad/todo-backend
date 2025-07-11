from pydantic import Field, validator
from typing import ClassVar
from datetime import datetime, timezone

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class ObjectIdValidatorMixin:
    @classmethod
    def validate_object_id(cls, v):
        if v is None:
            raise ValueError("Object ID cannot be None")
        if not PyObjectId.is_valid(v):
            raise ValueError(f"Invalid Object ID format: {v}")
        return v


class TeamModel(Document, ObjectIdValidatorMixin):
    """
    Model for teams.
    """

    collection_name: ClassVar[str] = "teams"

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    poc_id: PyObjectId | None = None
    created_by: PyObjectId
    updated_by: PyObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False

    @validator("created_by", "updated_by", "poc_id")
    def validate_object_id(cls, v):
        if v is None:
            return v
        return cls.validate_object_id(v)


class UserTeamDetailsModel(Document, ObjectIdValidatorMixin):
    """
    Model for user-team relationships.
    """

    collection_name: ClassVar[str] = "user_team_details"

    user_id: PyObjectId
    team_id: PyObjectId
    is_active: bool = True
    role_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: PyObjectId
    updated_by: PyObjectId

    @validator("user_id", "team_id", "created_by", "updated_by")
    def validate_object_ids(cls, v):
        return cls.validate_object_id(v)
