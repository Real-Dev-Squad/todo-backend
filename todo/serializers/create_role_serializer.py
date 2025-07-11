from rest_framework import serializers
from todo.constants.role import ROLE_TYPE_CHOICES, ROLE_SCOPE_CHOICES, RoleScope


class CreateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=ROLE_TYPE_CHOICES)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, default=RoleScope.GLOBAL.value)
    is_active = serializers.BooleanField(default=True)

    def validate_name(self, value):
        """
        Validate role name - check for blank values.
        Note: Uniqueness is validated at the service/repository layer
        to handle database constraints and race conditions properly.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Role name cannot be blank")
        return value.strip()

    def validate_description(self, value):
        if value:
            return value.strip()
        return value
