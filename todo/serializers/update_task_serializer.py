from rest_framework import serializers
from bson import ObjectId
from datetime import datetime, timezone

from todo.constants.task import TaskPriority, TaskStatus
from todo.constants.messages import ValidationErrors


class UpdateTaskSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255, help_text="Title of the task")
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, help_text="Description of the task"
    )
    priority = serializers.ChoiceField(
        required=False,
        choices=[priority.name for priority in TaskPriority],
        allow_null=True,
        help_text="Priority of the task (LOW, MEDIUM, HIGH)",
    )
    status = serializers.ChoiceField(
        required=False,
        choices=[status.name for status in TaskStatus],
        allow_null=True,
        help_text="Status of the task (TODO, IN_PROGRESS, DONE)",
    )
    assignee_id = serializers.CharField(
        required=False, allow_null=True, help_text="User or team ID to assign the task to"
    )
    user_type = serializers.ChoiceField(
        required=False, choices=["user", "team"], allow_null=True, help_text="Type of assignee: 'user' or 'team'"
    )
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="List of label IDs",
    )
    dueAt = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Due date and time in ISO format (UTC)"
    )
    startedAt = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Start date and time in ISO format (UTC)"
    )
    isAcknowledged = serializers.BooleanField(required=False, help_text="Whether the task is acknowledged")

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

    def validate(self, data):
        # Compose the 'assignee' dict if assignee_id and user_type are present
        assignee_id = data.pop("assignee_id", None)
        user_type = data.pop("user_type", None)
        if assignee_id and user_type:
            if not ObjectId.is_valid(assignee_id):
                raise serializers.ValidationError(
                    {"assignee_id": ValidationErrors.INVALID_OBJECT_ID.format(assignee_id)}
                )
            if user_type not in ["user", "team"]:
                raise serializers.ValidationError({"user_type": "user_type must be either 'user' or 'team'"})
            data["assignee"] = {"assignee_id": assignee_id, "user_type": user_type}
        return data
