from rest_framework import serializers
from bson import ObjectId

from todo.constants.messages import ValidationErrors


class UpdateTeamSerializer(serializers.Serializer):
    """
    Serializer for updating team details.
    All fields are optional for PATCH operations.
    """

    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    poc_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    member_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    def validate_name(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError("Team name cannot be blank")
        return value.strip() if value else None

    def validate_description(self, value):
        if value is not None:
            return value.strip()
        return value

    def validate_poc_id(self, value):
        if not value or not value.strip():
            return None
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(value))
        return value

    def validate_member_ids(self, value):
        for member_id in value:
            if not ObjectId.is_valid(member_id):
                raise serializers.ValidationError(ValidationErrors.INVALID_OBJECT_ID.format(member_id))
        return value
