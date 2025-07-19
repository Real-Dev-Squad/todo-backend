import uuid
from django.db import models
from .task import Task
from .user import User


class Watchlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "watchlist"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.task}"
