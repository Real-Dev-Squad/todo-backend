from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime


class CreateTaskAssignmentDTO(BaseModel):
    task_id: str
    assignee_id: str
    user_type: Literal["user", "team"]

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
    assignee_name: Optional[str] = None
    user_type: Literal["user", "team"]
    executor_id: Optional[str] = None  # User ID executing the task (for team assignments)
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
