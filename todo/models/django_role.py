from django.db import models
import uuid


class RoleScope(models.TextChoices):
    GLOBAL = "global", "Global"
    TEAM = "team", "Team"


class Role(models.Model):
    """
    Django model for roles, replacing the MongoDB-based RoleModel.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    scope = models.CharField(
        max_length=20,
        choices=RoleScope.choices,
        default=RoleScope.GLOBAL
    )
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'roles'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['scope']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.scope})"
