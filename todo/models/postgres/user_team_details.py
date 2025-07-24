import uuid
from django.db import models
from django.db.models.manager import Manager


class UserTeamDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="team_details")
    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="user_details")
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    role = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("User", on_delete=models.CASCADE, related_name="created_user_team_details")
    updated_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_user_team_details"
    )
    objects: Manager = models.Manager()

    class Meta:
        db_table = "user_team_details"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["team"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"User {self.user} in Team {self.team}"
