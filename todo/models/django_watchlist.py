from django.db import models
import uuid


class Watchlist(models.Model):
    """
    Django model for watchlist, replacing the MongoDB-based WatchlistModel.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.UUIDField()
    user_id = models.UUIDField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'watchlist'
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['task_id', 'user_id']
    
    def __str__(self):
        return f"User {self.user_id} watching Task {self.task_id}"
