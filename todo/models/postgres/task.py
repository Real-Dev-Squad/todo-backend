from django.db import models
from django.utils import timezone


class PostgresTask(models.Model):
    """
    Postgres model for tasks, mirroring MongoDB TaskModel structure.
    This enables future migration from MongoDB to Postgres.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Task fields
    display_id = models.CharField(max_length=100, null=True, blank=True)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    # Store the same format as MongoDB (integer for priority, string for status)
    priority = models.IntegerField(default=3)  # 1=HIGH, 2=MEDIUM, 3=LOW
    status = models.CharField(max_length=20, default="TODO")

    # Boolean fields
    is_acknowledged = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)

    # References (as strings for now, will be foreign keys in future)
    created_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
    updated_by = models.CharField(max_length=24, null=True, blank=True)

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
        db_table = "postgres_tasks"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["display_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["due_at"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.display_id or 'N/A'})"

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class PostgresTaskLabel(models.Model):
    """
    Junction table for task-label relationships.
    """

    task = models.ForeignKey(PostgresTask, on_delete=models.CASCADE, related_name="task_labels")
    label_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string

    class Meta:
        db_table = "postgres_task_labels"
        unique_together = ["task", "label_mongo_id"]
        indexes = [
            models.Index(fields=["label_mongo_id"]),
        ]


class PostgresDeferredDetails(models.Model):
    """
    Model for deferred task details.
    """

    task = models.OneToOneField(PostgresTask, on_delete=models.CASCADE, related_name="deferred_details")
    deferred_at = models.DateTimeField(null=True, blank=True)
    deferred_till = models.DateTimeField(null=True, blank=True)
    deferred_by = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string

    class Meta:
        db_table = "postgres_deferred_details"
