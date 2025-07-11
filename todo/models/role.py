from pydantic import Field, ConfigDict
from typing import ClassVar
from datetime import datetime

from todo.constants.role import RoleType, RoleScope
from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class RoleModel(Document):
    collection_name: ClassVar[str] = "roles"

    id: PyObjectId | None = Field(None, alias="_id")
    name: str
    description: str | None = None
    type: RoleType
    scope: RoleScope = RoleScope.GLOBAL
    is_active: bool = True
    created_by: str
    created_at: datetime
    updated_by: str | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(ser_enum="value", from_attributes=True, populate_by_name=True, use_enum_values=True)
