import uuid
from django.db import models
from django.db.models.manager import Manager


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey("Task", on_delete=models.CASCADE)
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    previous_executor = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="auditlog_previous_executor"
    )
    new_executor = models.ForeignKey("User", on_delete=models.CASCADE, related_name="auditlog_new_executor")
    spoc = models.ForeignKey("User", on_delete=models.CASCADE, related_name="auditlog_spoc")
    action = models.CharField(max_length=50, default="reassign_executor")
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="auditlog_updated_by"
    )
    objects: Manager = models.Manager()

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["team"]),
            models.Index(fields=["action"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"AuditLog for Task {self.task_id}"
