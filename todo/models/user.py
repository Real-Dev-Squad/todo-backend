from pydantic import Field
from typing import ClassVar
from datetime import datetime, timezone

from todo.models.common.document import Document


class UserModel(Document):
    """
    Model for external users authenticated via Google OAuth.
    Separate from internal RDS authenticated users.
    """

    collection_name: ClassVar[str] = "users"

    googleId: str
    emailId: str
    name: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime | None
