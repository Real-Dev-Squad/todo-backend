from rest_framework import serializers
from bson import ObjectId
from datetime import datetime, timezone

from todo.constants.task import TaskPriority, TaskStatus
from todo.constants.messages import ValidationErrors


class UpdateTaskSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    priority = serializers.ChoiceField(
        required=False,
        choices=[priority.name for priority in TaskPriority],
        allow_null=True,
    )
    status = serializers.ChoiceField(
        required=False,
        choices=[status.name for status in TaskStatus],
        allow_null=True,
    )
    assignee = serializers.DictField(required=False, allow_null=True)
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    dueAt = serializers.DateTimeField(required=False, allow_null=True)
    startedAt = serializers.DateTimeField(required=False, allow_null=True)
    isAcknowledged = serializers.BooleanField(required=False)

    def validate_title(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError(ValidationErrors.BLANK_TITLE)
        return value

    def validate_labels(self, value):
        if value is None:
            return value

        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError(ValidationErrors.INVALID_LABELS_STRUCTURE)

        invalid_ids = [label_id for label_id in value if not ObjectId.is_valid(label_id)]
        if invalid_ids:
            raise serializers.ValidationError(
                [ValidationErrors.INVALID_OBJECT_ID.format(label_id) for label_id in invalid_ids]
            )

        return value

    def validate_dueAt(self, value):
        if value is None:
            return value
        errors = []
        now = datetime.now(timezone.utc)
        if value <= now:
            errors.append(ValidationErrors.PAST_DUE_DATE)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate_startedAt(self, value):
        if value and value > datetime.now(timezone.utc):
            raise serializers.ValidationError(ValidationErrors.FUTURE_STARTED_AT)
        return value

    def validate_assignee(self, value):
        if not value:
            return None

        if not isinstance(value, dict):
            raise serializers.ValidationError("Assignee must be a dictionary")

        assignee_id = value.get("assignee_id")
        relation_type = value.get("relation_type")

        if not assignee_id:
            raise serializers.ValidationError("assignee_id is required")

        if not relation_type or relation_type not in ["team", "user"]:
            raise serializers.ValidationError("relation_type must be either 'team' or 'user'")

        if not ObjectId.is_valid(assignee_id):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(assignee_id))

        return value
