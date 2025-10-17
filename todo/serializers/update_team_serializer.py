from rest_framework import serializers
from bson import ObjectId

from todo.constants.messages import ValidationErrors


class UpdateTeamSerializer(serializers.Serializer):
    """
    Serializer for updating team details.

    """

    poc_id = serializers.CharField(required=True, allow_null=False, allow_blank=False)

    def validate_poc_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value
