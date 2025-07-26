from datetime import datetime, timezone
from typing import ClassVar
from pydantic import Field
from todo.models.common.document import Document
from todo.models.common.pyobjectid import PyObjectId


class AuditLogModel(Document):
    collection_name: ClassVar[str] = "audit_logs"

    task_id: PyObjectId | None = None
    team_id: PyObjectId | None = None
    previous_executor_id: PyObjectId | None = None
    new_executor_id: PyObjectId | None = None
    spoc_id: PyObjectId | None = None
    action: str  # e.g., "assigned_to_team", "unassigned_from_team", "status_changed", "reassign_executor", "team_created", "member_joined_team", "member_added_to_team", "member_removed_from_team", "team_updated"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # For status changes
    status_from: str | None = None
    status_to: str | None = None
    # For assignment changes
    assignee_from: PyObjectId | None = None
    assignee_to: PyObjectId | None = None
    # For general user reference (who performed the action)
    performed_by: PyObjectId | None = None
