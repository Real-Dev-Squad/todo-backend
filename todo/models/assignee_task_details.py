from pydantic import Field, validator
from typing import ClassVar, Literal
from datetime import datetime, timezone
from bson import ObjectId

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class AssigneeTaskDetailsModel(Document):
    """
    Model for assignee-task relationships.
    Supports single assignee (either team or user).
    """

    collection_name: ClassVar[str] = "assignee_task_details"

    id: PyObjectId | None = Field(None, alias="_id")
    assignee_id: PyObjectId  # Can be either team_id or user_id
    task_id: PyObjectId
    relation_type: Literal["team", "user"]
    is_action_taken: bool = False
    is_active: bool = True
    created_by: PyObjectId
    updated_by: PyObjectId | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    @validator("assignee_id", "task_id", "created_by", "updated_by")
    def validate_object_ids(cls, v):
        if v is None:
            return v
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return ObjectId(v)

    @validator("relation_type")
    def validate_relation_type(cls, v):
        if v not in ["team", "user"]:
            raise ValueError("relation_type must be either 'team' or 'user'")
        return v 