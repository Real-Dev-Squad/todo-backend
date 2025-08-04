from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId


class CreateTaskAssignmentDTO(BaseModel):
    task_id: str
    assignee_id: str
    user_type: Literal["user", "team"]
    original_team_id: Optional[str] = None

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

    @validator("original_team_id")
    def validate_original_team_id(cls, value):
        """Validate that the original team ID is a valid ObjectId if provided."""
        if value is not None and not ObjectId.is_valid(value):
            raise ValueError(f"Invalid original team ID: {value}")
        return value


class TaskAssignmentDTO(BaseModel):
    id: str
    task_id: str
    assignee_id: str
    assignee_name: Optional[str] = None
    user_type: Literal["user", "team"]
    executor_id: Optional[str] = None  # User ID executing the task (for team assignments)
    original_team_id: Optional[str] = None
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
    assignee_name: Optional[str] = None
    executor_id: Optional[str] = None  # User ID executing the task (for team assignments)
    is_active: bool
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
