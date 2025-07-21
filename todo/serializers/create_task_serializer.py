from rest_framework import serializers
from datetime import datetime, timezone
from todo.constants.task import TaskPriority, TaskStatus
from todo.constants.messages import ValidationErrors


class CreateTaskSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False, help_text="Title of the task")
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, help_text="Description of the task"
    )
    priority = serializers.ChoiceField(
        required=False,
        choices=[priority.name for priority in TaskPriority],
        default=TaskPriority.LOW.name,
        help_text="Priority of the task (LOW, MEDIUM, HIGH)",
    )
    status = serializers.ChoiceField(
        required=False,
        choices=[status.name for status in TaskStatus],
        default=TaskStatus.TODO.name,
        help_text="Status of the task (TODO, IN_PROGRESS, DONE)",
    )
    # Accept assignee_id and user_type at the top level
    assignee_id = serializers.CharField(
        required=False, allow_null=True, help_text="User or team ID to assign the task to"
    )
    user_type = serializers.ChoiceField(
        required=False, choices=["user", "team"], allow_null=True, help_text="Type of assignee: 'user' or 'team'"
    )
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of label IDs",
    )
    dueAt = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Due date and time in ISO format (UTC)"
    )

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(ValidationErrors.BLANK_TITLE)
        return value

    def validate_dueAt(self, value):
        if value is not None:
            now = datetime.now(timezone.utc)
            if value <= now:
                raise serializers.ValidationError(ValidationErrors.PAST_DUE_DATE)
        return value

    def validate(self, data):
        # Compose the 'assignee' dict if assignee_id and user_type are present
        assignee_id = data.pop("assignee_id", None)
        user_type = data.pop("user_type", None)
        if assignee_id and user_type:
            if user_type not in ["user", "team"]:
                raise serializers.ValidationError({"user_type": "user_type must be either 'user' or 'team'"})
            data["assignee"] = {"assignee_id": assignee_id, "user_type": user_type}
        return data
