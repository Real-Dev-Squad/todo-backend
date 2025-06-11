from rest_framework import serializers
from datetime import datetime, timezone


class DeferTaskSerializer(serializers.Serializer):
    deferredTill = serializers.DateTimeField()

    def validate_deferredTill(self, value):
        if value < datetime.now(timezone.utc):
            raise serializers.ValidationError("deferredTill cannot be in the past.")
        return value
