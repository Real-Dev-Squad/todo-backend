from rest_framework import serializers


class CreateWatchlistSerializer(serializers.Serializer):
    taskId = serializers.CharField(required=True)
