from rest_framework import serializers
from datetime import datetime, timezone
from todo.constants.messages import ValidationErrors


class DeferTaskSerializer(serializers.Serializer):
    deferred_till = serializers.DateTimeField(source="deferredTill")

    def validate_deferred_till(self, value):
        if value < datetime.now(timezone.utc):
            raise serializers.ValidationError(ValidationErrors.PAST_DEFERRED_TILL_DATE)
        return value
