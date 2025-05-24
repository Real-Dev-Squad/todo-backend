from rest_framework import serializers
from todo.models.common.pyobjectid import PyObjectId


class AddLabelSerializer(serializers.Serializer):
    label_id = serializers.CharField(required=True)

    def validate_label_id(self, value):
        try:
            return PyObjectId(value)
        except Exception:
            raise serializers.ValidationError("Invalid label ID format") 