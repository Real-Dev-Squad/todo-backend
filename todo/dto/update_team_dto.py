from pydantic import BaseModel, field_validator
from typing import Optional
from todo.repositories.user_repository import UserRepository


class UpdateTeamDTO(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    poc_id: Optional[str] = None
    member_ids: Optional[list[str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        """Validate that name is not empty if provided."""
        if value is not None and not value.strip():
            raise ValueError("Team name cannot be blank")
        return value.strip() if value else None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        """Validate that description is not empty if provided."""
        if value is not None:
            return value.strip()
        return value

    @field_validator("poc_id")
    @classmethod
    def validate_poc_id(cls, value):
        """Validate that the POC ID exists in the database if provided."""
        if value is None:
            return value

        user = UserRepository.get_by_id(value)
        if not user:
            raise ValueError(f"Invalid POC ID: {value}")
        return value

    @field_validator("member_ids")
    @classmethod
    def validate_member_ids(cls, value):
        """Validate that all member IDs exist in the database if provided."""
        if value is None:
            return value

        # Batch validate all member IDs in a single database query
        existing_users = UserRepository.get_by_ids(value)
        existing_ids = {str(user.id) for user in existing_users}
        invalid_ids = [member_id for member_id in value if member_id not in existing_ids]

        if invalid_ids:
            raise ValueError(f"Invalid member IDs: {invalid_ids}")
        return value
