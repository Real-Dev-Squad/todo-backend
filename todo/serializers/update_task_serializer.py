from rest_framework import serializers
from bson import ObjectId
from datetime import datetime, timezone

from todo.constants.task import TaskPriority, TaskStatus
from todo.constants.messages import ValidationErrors
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
    timezone = serializers.CharField(
        required=False, allow_null=True, help_text="IANA timezone string like 'Asia/Kolkata'"
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
        user_type = value.get("user_type")

        if not assignee_id:
            raise serializers.ValidationError("assignee_id is required")

        if not user_type or user_type not in ["team", "user"]:
            raise serializers.ValidationError("user_type must be either 'team' or 'user'")

        if not ObjectId.is_valid(assignee_id):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(assignee_id))

        return value

    def validate(self, data):
        due_at = data.get("dueAt")
        timezone_str = data.get("timezone")
        errors = {}
        if due_at is not None:
            if not timezone_str:
                errors["timezone"] = [ValidationErrors.REQUIRED_TIMEZONE]
            try:
                tz = ZoneInfo(timezone_str)
            except ZoneInfoNotFoundError:
                errors["timezone"] = [ValidationErrors.INVALID_TIMEZONE]

            now_date = datetime.now(tz).date()
            value_date = due_at.astimezone(tz).date()

            if value_date < now_date:
                errors["dueAt"] = [ValidationErrors.PAST_DUE_DATE]
            if errors:
                raise serializers.ValidationError(errors)
        return data
