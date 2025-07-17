from django.db import models
import uuid
from .task import Task


class AssigneeTaskDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignee_id = models.UUIDField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    relation_type = models.CharField(max_length=10)  # 'team' or 'user'
    is_action_taken = models.BooleanField(default=False)  # type: ignore[arg-type]
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    created_by = models.UUIDField()
    updated_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assignee_task_details"
        indexes = [
            models.Index(fields=["assignee_id"]),
            models.Index(fields=["task"]),
            models.Index(fields=["relation_type"]),
        ]

    def __str__(self):
        return f"{self.assignee_id} - {self.task} ({self.relation_type})"
