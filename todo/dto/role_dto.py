from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RoleDTO(BaseModel):
    """
    Role Data Transfer Object
    """

    id: str
    name: str
    description: Optional[str] = None
    type: str
    scope: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    @classmethod
    def from_model(cls, role_model):
        """
        Convert RoleModel to RoleDTO
        """
        return cls(
            id=str(role_model.id),
            name=role_model.name,
            description=role_model.description,
            type=role_model.type.value if hasattr(role_model.type, "value") else role_model.type,
            scope=role_model.scope.value if hasattr(role_model.scope, "value") else role_model.scope,
            is_active=role_model.is_active,
            created_by=role_model.created_by,
            created_at=role_model.created_at,
            updated_by=role_model.updated_by,
            updated_at=role_model.updated_at,
        )
