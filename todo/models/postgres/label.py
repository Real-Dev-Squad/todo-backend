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
    created_by = models.ForeignKey("User", on_delete=models.CASCADE, related_name="created_labels")
    updated_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_labels"
    )
    objects: Manager = models.Manager()

    class Meta:
        db_table = "labels"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return self.name
