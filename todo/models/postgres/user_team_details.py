import uuid
from django.db import models
from django.db.models.manager import Manager


class UserTeamDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    team_id = models.UUIDField()
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    role_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.UUIDField()
    updated_by = models.UUIDField(null=True, blank=True)
    objects: Manager = models.Manager()

    class Meta:
        db_table = "user_team_details"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["team_id"]),
            models.Index(fields=["role_id"]),
        ]

    def __str__(self):
        return f"User {self.user_id} in Team {self.team_id}"
