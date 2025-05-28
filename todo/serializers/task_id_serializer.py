from rest_framework import serializers
from bson import ObjectId
from bson.errors import InvalidId
from todo.constants.messages import ValidationErrors


class TaskIdSerializer(serializers.Serializer):
    task_id = serializers.CharField()

    def validate_task_id(self, value):
        try:
            ObjectId(value)
        except InvalidId:
            raise serializers.ValidationError(ValidationErrors.INVALID_TASK_ID_FORMAT)
        return value
