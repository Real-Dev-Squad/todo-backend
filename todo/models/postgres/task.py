import uuid
from django.db import models
from django.db.models.manager import Manager


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    is_acknowledged = models.BooleanField(default=False)  # type: ignore[arg-type]
    labels = models.JSONField(default=list, blank=True)
    is_deleted = models.BooleanField(default=False)  # type: ignore[arg-type]
    deferred_at = models.DateTimeField(null=True, blank=True)
    deferred_till = models.DateTimeField(null=True, blank=True)
    deferred_by = models.CharField(max_length=255, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    objects: Manager = models.Manager()

    class Meta:
        db_table = "tasks"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"
