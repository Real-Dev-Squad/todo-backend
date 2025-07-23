import uuid
from django.db import models
from .task import Task
from .user import User
from django.db.models.manager import Manager


class Watchlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="watchlist_items")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlists")
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_watchlists")
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_watchlists"
    )
    objects: Manager = models.Manager()

    class Meta:
        db_table = "watchlist"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.task}"
