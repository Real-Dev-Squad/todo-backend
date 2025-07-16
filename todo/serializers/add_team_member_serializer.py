from rest_framework import serializers


class AddTeamMemberSerializer(serializers.Serializer):
    member_ids = serializers.ListField(
        child=serializers.CharField(), min_length=1, help_text="List of user IDs to add to the team"
    )
