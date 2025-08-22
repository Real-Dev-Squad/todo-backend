from django.db import models
from django.utils import timezone


class PostgresUserRole(models.Model):
    """
    Postgres model for user roles.
    """
    
    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)
    
    # User role fields
    user_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    role_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    team_mongo_id = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string
    
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
            ('SYNCED', 'Synced'),
            ('PENDING', 'Pending'),
            ('FAILED', 'Failed'),
        ],
        default='SYNCED'
    )
    sync_error = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'postgres_user_roles'
        unique_together = ['user_mongo_id', 'role_mongo_id', 'team_mongo_id']
        indexes = [
            models.Index(fields=['mongo_id']),
            models.Index(fields=['user_mongo_id']),
            models.Index(fields=['role_mongo_id']),
            models.Index(fields=['team_mongo_id']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"User {self.user_mongo_id} has Role {self.role_mongo_id}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
