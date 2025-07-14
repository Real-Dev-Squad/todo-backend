from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from todo.models import Role


class RoleDTO(BaseModel):
    """
    Role Data Transfer Object
    """

    id: str
    name: str
    description: Optional[str] = None
    scope: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    @classmethod
    def from_model(cls, role_model: Role) -> "RoleDTO":
        """
        Convert Role to RoleDTO

        Args:
            role_model: The Role instance to convert

        Returns:
            RoleDTO: The converted data transfer object

        Raises:
            ValueError: If role_model is None or invalid
        """
        required_attrs = ["id", "name", "scope", "is_active", "created_by", "created_at"]
        if not all(hasattr(role_model, attr) for attr in required_attrs):
            raise ValueError(f"role_model must have all required attributes: {', '.join(required_attrs)}")

        scope_value = role_model.scope.value if hasattr(role_model.scope, "value") else str(role_model.scope)

        return cls(
            id=str(role_model.id),
            name=role_model.name,
            description=role_model.description,
            scope=scope_value,
            is_active=role_model.is_active,
            created_by=role_model.created_by,
            created_at=role_model.created_at,
            updated_by=role_model.updated_by,
            updated_at=role_model.updated_at,
        )
