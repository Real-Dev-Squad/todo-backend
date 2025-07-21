from rest_framework import serializers


class UpdateTeamSerializer(serializers.Serializer):
    """
    Serializer for updating team details.
    All fields are optional for PATCH operations.
    """

    name = serializers.CharField(max_length=100, required=False, allow_blank=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    poc_id = serializers.CharField(required=False, allow_null=True, allow_blank=False)
    member_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True, default=None)

    def validate_name(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError("Team name cannot be blank")
        return value.strip() if value else None

    def validate_description(self, value):
        if value is not None:
            return value.strip()
        return value

    def validate_poc_id(self, value):
        if not value or not value.strip():
            return None

    def validate_member_ids(self, value):
        if value is None:
            return value
