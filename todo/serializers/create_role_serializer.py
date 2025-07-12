from rest_framework import serializers
from todo.constants.role import ROLE_SCOPE_CHOICES, VALID_ROLE_NAMES_BY_SCOPE


class CreateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    scope = serializers.ChoiceField(choices=ROLE_SCOPE_CHOICES, default="GLOBAL")
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

    def validate(self, attrs):
        """
        Validate that the role name is valid for the given scope.
        """
        name = attrs.get("name")
        scope = attrs.get("scope")

        if name and scope:
            valid_names = VALID_ROLE_NAMES_BY_SCOPE.get(scope, [])
            if name not in valid_names:
                raise serializers.ValidationError(
                    {
                        "name": f"Invalid role name '{name}' for scope '{scope}'. "
                        f"Valid names are: {', '.join(valid_names)}"
                    }
                )

        return attrs

    def validate_description(self, value):
        if value:
            return value.strip()
        return value
