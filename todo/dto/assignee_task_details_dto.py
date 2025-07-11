from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId

from todo.repositories.user_repository import UserRepository
from todo.repositories.team_repository import TeamRepository


class CreateAssigneeTaskDetailsDTO(BaseModel):
    assignee_id: str
    relation_type: Literal["team", "user"]
    task_id: str

    @validator("assignee_id")
    def validate_assignee_id(cls, value):
        """Validate that the assignee ID exists in the database."""
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid assignee ID: {value}")
        return value

    @validator("task_id")
    def validate_task_id(cls, value):
        """Validate that the task ID exists in the database."""
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid task ID: {value}")
        return value

    @validator("relation_type")
    def validate_relation_type(cls, value):
        """Validate that the relation type is valid."""
        if value not in ["team", "user"]:
            raise ValueError("relation_type must be either 'team' or 'user'")
        return value


class AssigneeTaskDetailsDTO(BaseModel):
    id: str
    assignee_id: str
    task_id: str
    relation_type: Literal["team", "user"]
    is_action_taken: bool
    is_active: bool
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AssigneeInfoDTO(BaseModel):
    id: str
    name: str
    relation_type: Literal["team", "user"]
    is_action_taken: bool
    is_active: bool 