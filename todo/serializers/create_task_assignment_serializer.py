from rest_framework import serializers


class CreateTaskAssignmentSerializer(serializers.Serializer):
    task_id = serializers.CharField(required=True)
    assignee_id = serializers.CharField(required=True)
    user_type = serializers.ChoiceField(
        required=True, choices=["user", "team"], help_text="Type of assignee: 'user' or 'team'"
    )

    def validate_user_type(self, value):
        if value not in ["user", "team"]:
            raise serializers.ValidationError("user_type must be either 'user' or 'team'")
        return value


class AssignTaskToUserSerializer(serializers.Serializer):
    assignee_id = serializers.CharField(help_text="User ID to assign the task to")
