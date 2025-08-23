from django.db import models
from django.utils import timezone


class PostgresWatchlist(models.Model):
    """
    Postgres model for watchlists that matches MongoDB schema.
    This represents a user watching a specific task.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Core watchlist fields matching MongoDB schema
    task_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    user_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
    created_at = models.DateTimeField(default=timezone.now)
    updated_by = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string
    updated_at = models.DateTimeField(null=True, blank=True)

    # Sync metadata for dual write system
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
        db_table = "postgres_watchlist"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["task_id"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["sync_status"]),
            # Composite index for efficient queries
            models.Index(fields=["user_id", "task_id"]),
        ]
        # Ensure unique user-task combination
        unique_together = ["user_id", "task_id"]

    def __str__(self):
        return f"Watchlist: User {self.user_id} -> Task {self.task_id}"

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
