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
    user_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    team_mongo_id = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string
    
    # Status
    STATUS_CHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ASSIGNED'
    )
    
    # Timestamps
    assigned_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    # References
    assigned_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
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
        db_table = 'postgres_task_assignments'
        unique_together = ['task_mongo_id', 'user_mongo_id']
        indexes = [
            models.Index(fields=['mongo_id']),
            models.Index(fields=['task_mongo_id']),
            models.Index(fields=['user_mongo_id']),
            models.Index(fields=['team_mongo_id']),
            models.Index(fields=['status']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"Task {self.task_mongo_id} assigned to User {self.user_mongo_id}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
