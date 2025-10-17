from rest_framework import serializers
from bson import ObjectId

from todo.constants.messages import ValidationErrors


class UpdateTeamSerializer(serializers.Serializer):
    """
    Serializer for updating team details.

    """

    poc_id = serializers.CharField(required=False, allow_null=True, allow_blank=False)

    def validate_poc_id(self, value):
        if not value or not value.strip():
            return None
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value

    def validate(self, data):
        """Validate that the POC ID is provided if updating the POC."""
        if data.get("poc_id") is None:
            raise serializers.ValidationError(ValidationErrors.POC_NOT_PROVIDED)
        return data
