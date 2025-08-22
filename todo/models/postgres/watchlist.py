from django.db import models
from django.utils import timezone


class PostgresWatchlist(models.Model):
    """
    Postgres model for watchlists.
    """
    
    # MongoDB ObjectId as string for reference
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)
    
    # Watchlist fields
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    
    # References
    user_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    created_by = models.CharField(max_length=24)  # MongoDB ObjectId as string
    updated_by = models.CharField(max_length=24, null=True, blank=True)  # MongoDB ObjectId as string
    
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
        db_table = 'postgres_watchlists'
        indexes = [
            models.Index(fields=['mongo_id']),
            models.Index(fields=['user_mongo_id']),
            models.Index(fields=['created_by']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"{self.name} (User: {self.user_mongo_id})"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class PostgresWatchlistTask(models.Model):
    """
    Junction table for watchlist-task relationships.
    """
    watchlist = models.ForeignKey(PostgresWatchlist, on_delete=models.CASCADE, related_name='watchlist_tasks')
    task_mongo_id = models.CharField(max_length=24)  # MongoDB ObjectId as string
    
    class Meta:
        db_table = 'postgres_watchlist_tasks'
        unique_together = ['watchlist', 'task_mongo_id']
        indexes = [
            models.Index(fields=['task_mongo_id']),
        ]
