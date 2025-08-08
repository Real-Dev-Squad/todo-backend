from pydantic import Field, validator, ConfigDict
from typing import ClassVar
from datetime import datetime, timezone

from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId
from todo.constants.role import RoleScope, RoleName, VALID_ROLE_NAMES_BY_SCOPE


class UserRoleModel(Document):
    """User-role relationship model"""

    collection_name: ClassVar[str] = "user_roles"

    id: PyObjectId | None = Field(None, alias="_id")
    user_id: str
    role_name: RoleName
    scope: RoleScope
    team_id: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"

    model_config = ConfigDict(ser_enum="value", from_attributes=True, populate_by_name=True, use_enum_values=True)

    @validator("role_name")
    def validate_role_name(cls, v, values):
        """Validate role_name is valid for the given scope."""
        scope = values.get("scope")
        if scope and scope.value in VALID_ROLE_NAMES_BY_SCOPE:
            valid_roles = VALID_ROLE_NAMES_BY_SCOPE[scope.value]
            role_value = v.value if hasattr(v, "value") else v
            if role_value not in valid_roles:
                raise ValueError(f"Invalid role '{role_value}' for scope '{scope.value}'. Valid roles: {valid_roles}")
        return v

    @validator("team_id")
    def validate_team_id(cls, v, values):
        """Validate team_id requirements based on scope."""
        scope = values.get("scope")
        if scope == RoleScope.TEAM and not v:
            raise ValueError("team_id is required for TEAM scope roles")
        if scope == RoleScope.GLOBAL and v:
            raise ValueError("team_id should not be provided for GLOBAL scope roles")
        return v
