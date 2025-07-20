import uuid
from django.db import models
from django.db.models.manager import Manager


class Label(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)  # type: ignore[arg-type]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.UUIDField()
    updated_by = models.UUIDField(null=True, blank=True)
    objects: Manager = models.Manager()

    class Meta:
        db_table = "labels"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return self.name
