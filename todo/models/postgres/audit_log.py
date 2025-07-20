import uuid
from django.db import models
from django.db.models.manager import Manager


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.UUIDField()
    team_id = models.UUIDField()
    previous_executor_id = models.UUIDField(null=True, blank=True)
    new_executor_id = models.UUIDField()
    spoc_id = models.UUIDField()
    action = models.CharField(max_length=50, default="reassign_executor")
    timestamp = models.DateTimeField(auto_now_add=True)
    objects: Manager = models.Manager()

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["task_id"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"AuditLog for Task {self.task_id}"
