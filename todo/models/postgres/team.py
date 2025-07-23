import uuid
from django.db import models
from django.db.models.manager import Manager


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    poc = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="teams_as_poc")
    invite_code = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="created_teams",
    )
    updated_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_teams"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)  # type: ignore[arg-type]
    objects: Manager = models.Manager()

    class Meta:
        db_table = "teams"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["invite_code"]),
        ]

    def __str__(self):
        return self.name
