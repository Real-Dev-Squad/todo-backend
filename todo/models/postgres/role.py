from django.db import models
from django.utils import timezone


class PostgresRole(models.Model):
    """
    Postgres model for roles.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Role fields
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    permissions = models.JSONField(default=dict)  # Store permissions as JSON

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)

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
        db_table = "postgres_roles"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
