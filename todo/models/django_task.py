from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class TaskStatus(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"
    DEFERRED = "deferred", "Deferred"


class Task(models.Model):
    """
    Django model for tasks, replacing the MongoDB-based TaskModel.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.LOW
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO
    )
    is_acknowledged = models.BooleanField(default=False)
    labels = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True
    )
    is_deleted = models.BooleanField(default=False)
    
    # Deferred details
    deferred_at = models.DateTimeField(null=True, blank=True)
    deferred_till = models.DateTimeField(null=True, blank=True)
    deferred_by = models.CharField(max_length=255, null=True, blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.CharField(max_length=255)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'tasks'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.status})"
