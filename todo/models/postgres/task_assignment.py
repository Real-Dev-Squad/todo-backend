from django.db import models
from django.utils import timezone


class PostgresTaskAssignment(models.Model):
    """
    Postgres model for task assignments.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Assignment fields
    task_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    assignee_id = models.CharField(max_length=24)  # MongoDB ObjectId as string (user or team ID)
    user_type = models.CharField(max_length=10, choices=[("user", "User"), ("team", "Team")])  # user or team
    team_id = models.CharField(
        max_length=24, null=True, blank=True
    )  # MongoDB ObjectId as string (only for team assignments)
    is_active = models.BooleanField(default=True)  # Match MongoDB approach

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)

    # References
    created_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
    updated_by = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string

    # Sync metadata
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
        db_table = "postgres_task_assignments"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["task_mongo_id"]),
            models.Index(fields=["assignee_id"]),
            models.Index(fields=["user_type"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"Task {self.task_mongo_id} assigned to {self.user_type} {self.assignee_id}"

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
