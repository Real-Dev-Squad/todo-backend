from django.db import models
import uuid


class AssigneeTaskDetails(models.Model):
    """
    Django model for assignee-task relationships, replacing the MongoDB-based AssigneeTaskDetailsModel.
    Supports single assignee (either team or user).
    """
    
    RELATION_TYPES = [
        ('team', 'Team'),
        ('user', 'User'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignee_id = models.UUIDField()  # Can be either team_id or user_id
    task_id = models.UUIDField()
    relation_type = models.CharField(max_length=10, choices=RELATION_TYPES)
    is_action_taken = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.UUIDField()
    updated_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignee_task_details'
        indexes = [
            models.Index(fields=['assignee_id']),
            models.Index(fields=['task_id']),
            models.Index(fields=['relation_type']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['assignee_id', 'task_id', 'relation_type']
    
    def __str__(self):
        return f"{self.relation_type.title()} {self.assignee_id} assigned to Task {self.task_id}"
