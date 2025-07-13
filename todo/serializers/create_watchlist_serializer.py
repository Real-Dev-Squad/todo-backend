from rest_framework import serializers
from bson import ObjectId

from todo.constants.messages import ValidationErrors


class CreateWatchlistSerializer(serializers.Serializer):
    taskId = serializers.CharField(required=True)

    def validate_taskId(self, value):
        try:
            ObjectId(str(value))
        except Exception:
            raise serializers.ValidationError(ValidationErrors.INVALID_TASK_ID_FORMAT)
        return value
