from pydantic import BaseModel, validator
from typing import Optional
from todo.repositories.user_repository import UserRepository


class UpdateTeamDTO(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    poc_id: Optional[str] = None
    member_ids: Optional[list[str]] = None

    @validator("name")
    def validate_name(cls, value):
        """Validate that name is not empty if provided."""
        if value is not None and not value.strip():
            raise ValueError("Team name cannot be blank")
        return value.strip() if value else None

    @validator("description")
    def validate_description(cls, value):
        """Validate that description is not empty if provided."""
        if value is not None:
            return value.strip()
        return value

    @validator("poc_id")
    def validate_poc_id(cls, value):
        """Validate that the POC ID exists in the database if provided."""
        if value is None:
            return value

        user = UserRepository.get_by_id(value)
        if not user:
            raise ValueError(f"Invalid POC ID: {value}")
        return value

    @validator("member_ids")
    def validate_member_ids(cls, value):
        """Validate that all member IDs exist in the database if provided."""
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
