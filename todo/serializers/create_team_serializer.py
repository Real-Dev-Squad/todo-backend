from bson import ObjectId
from rest_framework import serializers

from todo.constants.messages import ValidationErrors


class CreateTeamSerializer(serializers.Serializer):
    """
    The poc_id represents the team's point of contact and is optional.
    """

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    member_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    poc_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

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


class JoinTeamByInviteCodeSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=100)
