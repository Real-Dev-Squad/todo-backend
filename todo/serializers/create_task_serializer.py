from rest_framework import serializers
from bson import ObjectId
from datetime import datetime, timezone
from todo.constants.task import TaskPriority, TaskStatus


class CreateTaskSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    priority = serializers.ChoiceField(
        required=False,
        choices=[priority.name for priority in TaskPriority],
        default=TaskPriority.LOW.name,
    )
    status = serializers.ChoiceField(
        required=False,
        choices=[status.name for status in TaskStatus],
        default=TaskStatus.TODO.name,
    )
    assignee = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    dueAt = serializers.DateTimeField(required=False, allow_null=True)

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title must not be blank.")
        return value

    def validate_labels(self, value):
        for label_id in value:
            if not ObjectId.is_valid(label_id):
                raise serializers.ValidationError(f"{label_id} is not a valid ObjectId.")
        return value

    def validate_dueAt(self, value):
        if value is not None:
            now = datetime.now(timezone.utc)
            if value <= now:
                raise serializers.ValidationError("Due date must be in the future.")
        return value

    def validate_assignee(self, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value
