from datetime import datetime, timezone
from typing import ClassVar
from pydantic import Field
from todo.models.common.document import Document


class AuditLogModel(Document):
    collection_name: ClassVar[str] = "audit_logs"

    task_id: str
    team_id: str
    previous_executor_id: str | None = None
    new_executor_id: str
    spoc_id: str
    action: str = "reassign_executor"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
