from django.db import models
import uuid


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    scope = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)  # type: ignore[arg-type]
    created_by = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.UUIDField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "roles"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["scope"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.scope})"
