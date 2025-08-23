from django.db import models
from django.utils import timezone


class PostgresUserRole(models.Model):
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    user_id = models.CharField(max_length=24)
    role_name = models.CharField(max_length=50)
    scope = models.CharField(max_length=20)
    team_id = models.CharField(max_length=24, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=24, default="system")

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
        db_table = "postgres_user_roles"
        unique_together = ["user_id", "role_name", "scope", "team_id"]
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["role_name"]),
            models.Index(fields=["scope"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"User {self.user_id} has Role {self.role_name} ({self.scope})"
