from django.db import models
import uuid
from .user import User
from .team import Team
from .role import Role


class UserTeamDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField()
    updated_by = models.UUIDField()

    class Meta:
        db_table = "user_team_details"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["team"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user} in {self.team} as {self.role}"
