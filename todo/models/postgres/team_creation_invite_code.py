from django.db import models
from django.utils import timezone


class PostgresTeamCreationInviteCode(models.Model):
    """
    Postgres model for team creation invite codes, mirroring MongoDB TeamCreationInviteCodeModel structure.
    This enables future migration from MongoDB to Postgres.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Invite code fields
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    # User references
    created_by = models.CharField(max_length=24)
    used_by = models.CharField(max_length=24, null=True, blank=True)

    # Status and timestamps
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    used_at = models.DateTimeField(null=True, blank=True)

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
        db_table = "postgres_team_creation_invite_codes"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["code"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["is_used"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"Invite Code: {self.code} ({'Used' if self.is_used else 'Unused'})"

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        super().save(*args, **kwargs)
