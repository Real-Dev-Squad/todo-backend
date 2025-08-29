from django.db import models
from django.utils import timezone


class PostgresTeam(models.Model):
    """
    Postgres model for teams, mirroring MongoDB TeamModel structure.
    This enables future migration from MongoDB to Postgres.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # Team fields
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    invite_code = models.CharField(max_length=100, unique=True)

    # References (as strings for now, will be foreign keys in future)
    poc_id = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string
    created_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
    updated_by = models.CharField(max_length=24)  # MongoDB ObjectId as string

    # Boolean fields
    is_deleted = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

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
        db_table = "postgres_teams"
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["invite_code"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class PostgresUserTeamDetails(models.Model):
    """
    Postgres model for user-team relationships, mirroring MongoDB UserTeamDetailsModel structure.
    """

    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)

    # References (as strings for now, will be foreign keys in future)
    user_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    team_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    created_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
    updated_by = models.CharField(max_length=24)  # MongoDB ObjectId as string

    # Boolean fields
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

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
        db_table = "postgres_user_team_details"
        unique_together = ["user_id", "team_id"]
        indexes = [
            models.Index(fields=["mongo_id"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["sync_status"]),
        ]

    def __str__(self):
        return f"User {self.user_id} in Team {self.team_id}"

    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
