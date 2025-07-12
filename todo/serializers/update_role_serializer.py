from rest_framework import serializers
from todo.constants.role import ROLE_SCOPE_CHOICES


class UpdateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_name(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError("Role name cannot be blank")
        return value.strip() if value else None

    def validate_description(self, value):
        if value:
            return value.strip()
        return value
