from rest_framework import serializers
from todo.constants.role import ROLE_TYPE_CHOICES, ROLE_SCOPE_CHOICES


class RoleQuerySerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False, default=None, allow_null=True)
    type = serializers.ChoiceField(choices=ROLE_TYPE_CHOICES, required=False)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, required=False)

    def validate_is_active(self, value):
        return value
