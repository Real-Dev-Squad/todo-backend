from rest_framework import serializers
from todo.constants.role import ROLE_TYPE_CHOICES, ROLE_SCOPE_CHOICES


class UpdateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=ROLE_TYPE_CHOICES, required=False)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)
    updated_by = serializers.CharField(max_length=100)

    def validate_name(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError("Role name cannot be blank")
        return value.strip() if value else None

    def validate_updated_by(self, value):
        if not value.strip():
            raise serializers.ValidationError("Updated by cannot be blank")
        return value.strip()
