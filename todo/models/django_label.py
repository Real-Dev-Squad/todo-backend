from django.db import models
import uuid


class Label(models.Model):
    """
    Django model for labels, replacing the MongoDB-based LabelModel.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=7)  # Hex color code
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'labels'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return self.name
