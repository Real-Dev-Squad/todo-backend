from rest_framework import serializers


class GenerateTeamInviteCodeSerializer(serializers.Serializer):
    """Serializer for generating team invite codes."""

    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional description for the team invite code (e.g., 'Code for marketing team')",
    )


class VerifyTeamInviteCodeSerializer(serializers.Serializer):
    """Serializer for verifying team invite codes."""

    code = serializers.CharField(max_length=20, min_length=6, help_text="The team invite code to verify")
