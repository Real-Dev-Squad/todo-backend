from unittest import TestCase
from rest_framework.exceptions import ValidationError

from todo.constants.task import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
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
        self.assertEqual(serializer.validated_data["limit"], DEFAULT_PAGE_LIMIT)

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
        data = {"limit": f"{MAX_PAGE_LIMIT + 1}"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(f"Ensure this value is less than or equal to {MAX_PAGE_LIMIT}", str(context.exception))

    def test_serializer_handles_partial_input_gracefully(self):
        data = {"page": "3"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 3)
        self.assertEqual(serializer.validated_data["limit"], DEFAULT_PAGE_LIMIT)

    def test_serializer_ignores_undefined_extra_fields(self):
        data = {"page": "2", "limit": "5", "extra_field": "ignored"}
        serializer = GetTaskQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 2)
        self.assertEqual(serializer.validated_data["limit"], 5)
        self.assertNotIn("extra_field", serializer.validated_data)
