from rest_framework import serializers

from todo.constants.messages import ValidationErrors


class UpdateWatchlistSerializer(serializers.Serializer):
    isActive = serializers.BooleanField(required=True)

    def validate_isActive(self, value):
        if value is None:
            raise serializers.ValidationError(ValidationErrors.INVALID_IS_ACTIVE_VALUE)
        return value
