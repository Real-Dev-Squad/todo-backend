import uuid
from django.db import models
from django.core.validators import EmailValidator


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    google_id = models.CharField(max_length=255, unique=True, db_index=True)
    email_id = models.EmailField(validators=[EmailValidator()])
    name = models.CharField(max_length=255)
    picture = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["email_id"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.email_id})"
