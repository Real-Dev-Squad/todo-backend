from rest_framework import serializers
from todo.constants.role import ROLE_TYPE_CHOICES, ROLE_SCOPE_CHOICES, RoleScope


class CreateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=ROLE_TYPE_CHOICES)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, default=RoleScope.GLOBAL.value)
    is_active = serializers.BooleanField(default=True)
    created_by = serializers.CharField(max_length=100)

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Role name cannot be blank")
        return value.strip()

    def validate_created_by(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Created by cannot be blank")
        return value.strip()

    def validate_description(self, value):
        if value:
            return value.strip()
        return value