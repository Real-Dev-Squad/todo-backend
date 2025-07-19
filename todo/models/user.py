from pydantic import Field, EmailStr
from typing import ClassVar
from datetime import datetime, timezone

from todo.models.common.document import Document


class UserModel(Document):
    """
    Model for external users authenticated via Google OAuth.
    Separate from internal RDS authenticated users.
    """

    collection_name: ClassVar[str] = "users"

    google_id: str
    email_id: EmailStr
    name: str
    picture: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
