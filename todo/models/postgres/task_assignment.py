from django.db import models
import uuid
from .task import Task


class TaskAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    assignee_id = models.UUIDField()
    user_type = models.CharField(max_length=10)  # 'user' or 'team'
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    created_by = models.UUIDField()
    updated_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "task_assignment"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["assignee_id"]),
            models.Index(fields=["user_type"]),
        ]

    def __str__(self):
        return f"{self.task} - {self.assignee_id} ({self.user_type})"
