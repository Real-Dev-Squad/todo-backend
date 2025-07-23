import uuid
from django.db import models
from django.db.models.manager import Manager


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    priority = models.IntegerField()
    status = models.CharField(max_length=20)
    assignee = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    is_acknowledged = models.BooleanField(default=False)  # type: ignore[arg-type]
    labels = models.JSONField(default=list, blank=True)
    is_deleted = models.BooleanField(default=False)  # type: ignore[arg-type]
    deferred_at = models.DateTimeField(null=True, blank=True)
    deferred_till = models.DateTimeField(null=True, blank=True)
    deferred_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="deferred_tasks"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, related_name="created_tasks")
    updated_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_tasks"
    )
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
