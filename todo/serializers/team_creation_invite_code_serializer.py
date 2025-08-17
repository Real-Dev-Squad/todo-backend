from rest_framework import serializers


class GenerateTeamCreationInviteCodeSerializer(serializers.Serializer):
    """Serializer for generating team creation invite codes."""

    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional description for the team creation invite code (e.g., 'Code for marketing team')",
    )


class VerifyTeamCreationInviteCodeSerializer(serializers.Serializer):
    """Serializer for verifying team creation invite codes."""

    code = serializers.CharField(max_length=20, min_length=6, help_text="The team creation invite code to verify")
