from rest_framework import serializers


class CreateTeamSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    member_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    poc_id = serializers.CharField(required=True, allow_null=False)
