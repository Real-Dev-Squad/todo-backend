from pydantic import Field, validator
from typing import ClassVar, Literal
from datetime import datetime, timezone
from bson import ObjectId

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class TaskAssignmentModel(Document):
    """
    Model for task assignments to users or teams.
    """

    collection_name: ClassVar[str] = "task_details"

    id: PyObjectId | None = Field(None, alias="_id")
    task_id: PyObjectId
    assignee_id: PyObjectId  # Can be either team_id or user_id
    user_type: Literal["user", "team"]  # Changed from relation_type to user_type as requested
    is_active: bool = True
    created_by: PyObjectId
    updated_by: PyObjectId | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    executor_id: PyObjectId | None = None  # User within the team who is executing the task
    original_team_id: PyObjectId | None = None  # Track the original team when reassigned from team to user

    @validator("task_id", "assignee_id", "created_by", "updated_by", "original_team_id")
    def validate_object_ids(cls, v):
        if v is None:
            return v
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return ObjectId(v)

    @validator("user_type")
    def validate_user_type(cls, v):
        if v not in ["user", "team"]:
            raise ValueError("user_type must be either 'user' or 'team'")
        return v
