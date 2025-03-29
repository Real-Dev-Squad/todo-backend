from unittest import TestCase
from rest_framework.exceptions import ValidationError
from django.conf import settings

from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer


class GetTaskQueryParamsSerializerTest(TestCase):
    def test_serializer_validates_and_returns_valid_input(self):
        data = {"page": "2", "limit": "5"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 2)
        self.assertEqual(serializer.validated_data["limit"], 5)

    def test_serializer_applies_default_values_for_missing_fields(self):
        serializer = GetTaskQueryParamsSerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 1)
        self.assertEqual(
            serializer.validated_data["limit"],
            settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"],
        )

    def test_serializer_raises_error_for_page_below_min_value(self):
        data = {"page": "0"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("page must be greater than or equal to 1", str(context.exception))

    def test_serializer_raises_error_for_limit_below_min_value(self):
        data = {"limit": "0"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("limit must be greater than or equal to 1", str(context.exception))

    def test_serializer_raises_error_for_limit_above_max_value(self):
        max_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
        data = {"limit": f"{max_limit + 1}"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(f"Ensure this value is less than or equal to {max_limit}", str(context.exception))

    def test_serializer_handles_partial_input_gracefully(self):
        data = {"page": "3"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 3)
        self.assertEqual(
            serializer.validated_data["limit"],
            settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"],
        )

    def test_serializer_ignores_undefined_extra_fields(self):
        data = {"page": "2", "limit": "5", "extra_field": "ignored"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 2)
        self.assertEqual(serializer.validated_data["limit"], 5)
        self.assertNotIn("extra_field", serializer.validated_data)

    def test_serializer_uses_django_settings_values(self):
        """Test that the serializer correctly uses values from Django settings"""
        # Instead of mocking, we'll test against the actual settings values
        serializer = GetTaskQueryParamsSerializer(data={})
        self.assertTrue(serializer.is_valid())

        # Verify the serializer uses the values from settings
        self.assertEqual(
            serializer.validated_data["limit"],
            settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"],
        )

        # Test max value constraint using the actual max value
        max_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
        data = {"limit": f"{max_limit + 1}"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(f"Ensure this value is less than or equal to {max_limit}", str(context.exception))
