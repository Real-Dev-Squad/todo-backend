from rest_framework import serializers
from datetime import datetime, timezone
from todo.constants.messages import ValidationErrors


class DeferTaskSerializer(serializers.Serializer):
    deferredTill = serializers.DateTimeField()

    def validate_deferredTill(self, value):
        if value < datetime.now(timezone.utc):
            raise serializers.ValidationError(ValidationErrors.PAST_DEFERRED_TILL_DATE)
        return value
