from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime
from todo.repositories.user_repository import UserRepository


class CreateTeamDTO(BaseModel):
    name: str
    description: Optional[str] = None
    member_ids: Optional[List[str]] = None
    poc_id: Optional[str] = None

    @validator("member_ids")
    def validate_member_ids(cls, value):
        """Validate that all member IDs exist in the database."""
        if value is None:
            return value

        invalid_ids = []
        for member_id in value:
            user = UserRepository.get_by_id(member_id)
            if not user:
                invalid_ids.append(member_id)

        if invalid_ids:
            raise ValueError(f"Invalid member IDs: {invalid_ids}")
        return value

    @validator("poc_id")
    def validate_poc_id(cls, value):
        """Validate that the POC ID exists in the database."""
        if value is None:
            return value

        user = UserRepository.get_by_id(value)
        if not user:
            raise ValueError(f"Invalid POC ID: {value}")
        return value


class TeamDTO(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    poc_id: Optional[str] = None
    invite_code: Optional[str] = None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
