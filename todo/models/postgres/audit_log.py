from django.db import models
from django.utils import timezone


class PostgresAuditLog(models.Model):
    """
    Postgres model for audit logs.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Audit log fields
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("READ", "Read"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
    ]

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    collection_name = models.CharField(max_length=100)
    document_id = models.CharField(max_length=24)  # MongoDB ObjectId as string

    # User who performed the action
    user_mongo_id = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string

    # Changes made
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now)

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
        db_table = "postgres_audit_logs"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["collection_name"]),
            models.Index(fields=["document_id"]),
            models.Index(fields=["user_mongo_id"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.collection_name}:{self.document_id}"
