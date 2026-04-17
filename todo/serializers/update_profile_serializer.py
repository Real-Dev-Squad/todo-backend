from rest_framework import serializers


ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_FILE_SIZE = 5 * 1024 * 1024


class UpdateProfileSerializer(serializers.Serializer):
    picture = serializers.FileField(required=True)

    def validate_picture(self, value):
        if value.content_type not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}")

        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError("File size must be under 5MB")

        return value
