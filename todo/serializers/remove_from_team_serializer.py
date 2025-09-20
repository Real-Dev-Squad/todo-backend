from rest_framework import serializers
from bson import ObjectId
from todo.constants.messages import ValidationErrors


class RemoveFromTeamSerializer(serializers.Serializer):
    team_id = serializers.CharField()
    user_id = serializers.CharField()

    def validate_team_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value

    def validate_user_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value
