from rest_framework import serializers


class UpdateWatchlistSerializer(serializers.Serializer):
    isActive = serializers.BooleanField(required=True)
