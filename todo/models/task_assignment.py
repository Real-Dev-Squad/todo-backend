from pydantic import Field, validator
from typing import ClassVar, Literal
from datetime import datetime, timezone

from todo.models.common.document import Document


class TaskAssignmentModel(Document):
    """
    Model for task assignments to users or teams.
    """

    collection_name: ClassVar[str] = "task_details"

    id: str | None = Field(None, alias="_id")
    task_id: str
    assignee_id: str  # Can be either team_id or user_id
    user_type: Literal["user", "team"]  # Changed from relation_type to user_type as requested
    is_active: bool = True
    created_by: str
    updated_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    executor_id: str | None = None  # User within the team who is executing the task

    @validator("user_type")
    def validate_user_type(cls, v):
        if v not in ["user", "team"]:
            raise ValueError("user_type must be either 'user' or 'team'")
        return v
