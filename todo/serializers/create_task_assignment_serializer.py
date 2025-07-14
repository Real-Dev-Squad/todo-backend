from rest_framework import serializers
from bson import ObjectId
from todo.constants.messages import ValidationErrors


class CreateTaskAssignmentSerializer(serializers.Serializer):
    task_id = serializers.CharField(required=True)
    assignee_id = serializers.CharField(required=True)
    user_type = serializers.ChoiceField(
        required=True, choices=["user", "team"], help_text="Type of assignee: 'user' or 'team'"
    )

    def validate_task_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value

    def validate_assignee_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value

    def validate_user_type(self, value):
        if value not in ["user", "team"]:
            raise serializers.ValidationError("user_type must be either 'user' or 'team'")
        return value
