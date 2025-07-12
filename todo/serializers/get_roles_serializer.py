from rest_framework import serializers
from todo.constants.role import ROLE_SCOPE_CHOICES


class RoleQuerySerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False, default=None, allow_null=True)
    name = serializers.CharField(required=False, max_length=100)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, required=False)
