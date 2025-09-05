from django.db import models
from django.utils import timezone


class PostgresAuditLog(models.Model):
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    task_id = models.CharField(max_length=24, null=True, blank=True)
    team_id = models.CharField(max_length=24, null=True, blank=True)
    previous_executor_id = models.CharField(max_length=24, null=True, blank=True)
    new_executor_id = models.CharField(max_length=24, null=True, blank=True)
    spoc_id = models.CharField(max_length=24, null=True, blank=True)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=timezone.now)
    status_from = models.CharField(max_length=20, null=True, blank=True)
    status_to = models.CharField(max_length=20, null=True, blank=True)
    assignee_from = models.CharField(max_length=24, null=True, blank=True)
    assignee_to = models.CharField(max_length=24, null=True, blank=True)
    performed_by = models.CharField(max_length=24, null=True, blank=True)
    task_count = models.IntegerField(null=True, blank=True)

    last_sync_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ("SYNCED", "Synced"),
            ("PENDING", "Pending"),
            ("FAILED", "Failed"),
        ],
        default="SYNCED",
    )
    sync_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "postgres_audit_logs"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["task_id"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["performed_by"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"{self.action} on task {self.task_id}"
