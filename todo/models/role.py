from pydantic import Field, ConfigDict
from typing import ClassVar
from datetime import datetime

from todo.constants.role import RoleScope
from todo.models.common.document import Document


class RoleModel(Document):
    collection_name: ClassVar[str] = "roles"

    id: str | None = Field(None, alias="_id")
    name: str
    description: str | None = None
    scope: RoleScope = RoleScope.GLOBAL
    is_active: bool = True
    created_by: str
    created_at: datetime
    updated_by: str | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(ser_enum="value", from_attributes=True, populate_by_name=True, use_enum_values=True)
