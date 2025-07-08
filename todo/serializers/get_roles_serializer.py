from rest_framework import serializers
from todo.constants.role import ROLE_TYPE_CHOICES, ROLE_SCOPE_CHOICES


class GetRolesQuerySerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    type = serializers.ChoiceField(choices=ROLE_TYPE_CHOICES, required=False)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, required=False)
