from datetime import datetime, timezone
from typing import ClassVar
from pydantic import Field
from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId

class AuditLogModel(Document):
    collection_name: ClassVar[str] = "audit_logs"

    task_id: PyObjectId
    team_id: PyObjectId
    previous_executor_id: PyObjectId | None = None
    new_executor_id: PyObjectId
    spoc_id: PyObjectId
    action: str = "reassign_executor"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) 