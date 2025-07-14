from django.db import models
import uuid


class Team(models.Model):
    """
    Django model for teams, replacing the MongoDB-based TeamModel.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    poc_id = models.UUIDField(null=True, blank=True)
    invite_code = models.CharField(max_length=255, unique=True)
    created_by = models.UUIDField()
    updated_by = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'teams'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['invite_code']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return self.name


class UserTeamDetails(models.Model):
    """
    Django model for user-team relationships, replacing the MongoDB-based UserTeamDetailsModel.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    team_id = models.UUIDField()
    is_active = models.BooleanField(default=True)
    role_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField()
    updated_by = models.UUIDField()
    
    class Meta:
        db_table = 'user_team_details'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['team_id']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['user_id', 'team_id']
    
    def __str__(self):
        return f"User {self.user_id} in Team {self.team_id}"
