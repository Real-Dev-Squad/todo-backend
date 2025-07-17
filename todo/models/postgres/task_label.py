from django.db import models
import uuid
from .task import Task
from .label import Label


class TaskLabel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        db_table = "task_labels"
        unique_together = (("task", "label"),)

    def __str__(self):
        return f"{self.task} - {self.label}"
