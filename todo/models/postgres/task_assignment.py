import uuid
from django.db import models
from .task import Task
from django.db.models.manager import Manager


class TaskAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    assignee_user = models.ForeignKey(
        "User", on_delete=models.CASCADE, null=True, blank=True, related_name="assigned_tasks_as_user"
    )
    assignee_team = models.ForeignKey(
        "Team", on_delete=models.CASCADE, null=True, blank=True, related_name="assigned_tasks_as_team"
    )
    user_type = models.CharField(max_length=10)  # 'user' or 'team'
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    created_by = models.ForeignKey("User", on_delete=models.CASCADE, related_name="created_task_assignments")
    updated_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_task_assignments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    objects: Manager = models.Manager()

    class Meta:
        db_table = "task_assignment"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["assignee_user"]),
            models.Index(fields=["assignee_team"]),
            models.Index(fields=["user_type"]),
        ]

    def __str__(self):
        if self.user_type == "user":
            return f"{self.task} - {self.assignee_user} (user)"
        elif self.user_type == "team":
            return f"{self.task} - {self.assignee_team} (team)"
        else:
            return f"{self.task} - Unknown Assignee"
