from rest_framework import serializers


class CreateTeamSerializer(serializers.Serializer):
    """
    The poc_id represents the team's point of contact and is optional.
    """

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    member_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    poc_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class JoinTeamByInviteCodeSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=100)
