from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId


class CreateTaskAssignmentDTO(BaseModel):
    task_id: str
    assignee_id: str
    user_type: Literal["user", "team"]

    @validator("task_id")
    def validate_task_id(cls, value):
        """Validate that the task ID is a valid ObjectId."""
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid task ID: {value}")
        return value

    @validator("assignee_id")
    def validate_assignee_id(cls, value):
        """Validate that the assignee ID is a valid ObjectId."""
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid assignee ID: {value}")
        return value

    @validator("user_type")
    def validate_user_type(cls, value):
        """Validate that the user type is valid."""
        if value not in ["user", "team"]:
            raise ValueError("user_type must be either 'user' or 'team'")
        return value


class TaskAssignmentDTO(BaseModel):
    id: str
    task_id: str
    assignee_id: str
    user_type: Literal["user", "team"]
    is_active: bool
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TaskAssignmentResponseDTO(BaseModel):
    id: str
    task_id: str
    assignee_id: str
    user_type: Literal["user", "team"]
    assignee_name: str
    is_active: bool
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
