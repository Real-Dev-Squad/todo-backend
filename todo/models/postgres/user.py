from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class PostgresUser(models.Model):
    """
    Postgres model for users, mirroring MongoDB UserModel structure.
    This enables future migration from MongoDB to Postgres.
    """
    
    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)
    
    # User fields
    google_id = models.CharField(max_length=255, unique=True)
    email_id = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    picture = models.URLField(max_length=500, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    # Sync metadata
    last_sync_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('SYNCED', 'Synced'),
            ('PENDING', 'Pending'),
            ('FAILED', 'Failed'),
        ],
        default='SYNCED'
    )
    sync_error = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'postgres_users'
        indexes = [
            models.Index(fields=['mongo_id']),
            models.Index(fields=['google_id']),
            models.Index(fields=['email_id']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.email_id})"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
