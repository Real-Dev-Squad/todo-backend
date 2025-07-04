from unittest import TestCase
from rest_framework.exceptions import ValidationError
from django.conf import settings

from todo.serializers.get_labels_serializer import GetLabelQueryParamsSerializer
from todo.constants.messages import ValidationErrors


class GetLabelQueryParamsSerializerTest(TestCase):
    def test_get_labels_serializer_validates_and_returns_valid_input(self):
        data = {"page": "2", "limit": "5", "search": "urgent"}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 2)
        self.assertEqual(serializer.validated_data["limit"], 5)
        self.assertEqual(serializer.validated_data["search"], "urgent")

    def test_get_labels_serializer_applies_default_values_for_missing_fields(self):
        serializer = GetLabelQueryParamsSerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["page"], 1)
        self.assertEqual(serializer.validated_data["limit"], 10)
        self.assertEqual(serializer.validated_data["search"], "")

    def test_get_labels_serializer_allows_blank_search(self):
        data = {"search": ""}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["search"], "")

    def test_get_labels_serializer_raises_error_for_page_below_min_value(self):
        data = {"page": "0"}
        serializer = GetLabelQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(ValidationErrors.PAGE_POSITIVE, str(context.exception))

    def test_get_labels_serializer_raises_error_for_limit_below_min_value(self):
        data = {"limit": "0"}
        serializer = GetLabelQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(ValidationErrors.LIMIT_POSITIVE, str(context.exception))

    def test_get_labels_serializer_raises_error_for_limit_above_max_value(self):
        max_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
        data = {"limit": f"{max_limit + 1}"}
        serializer = GetLabelQueryParamsSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(f"Ensure this value is less than or equal to {max_limit}", str(context.exception))

    def test_get_labels_serializer_handles_partial_input_gracefully(self):
        data = {"limit": "20"}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["limit"], 20)
        self.assertEqual(serializer.validated_data["page"], 1)
        self.assertEqual(serializer.validated_data["search"], "")

    def test_get_labels_serializer_ignores_extra_fields(self):
        data = {"page": "1", "limit": "5", "search": "abc", "extra": "value"}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("extra", serializer.validated_data)

    def test_get_labels_serializer_uses_max_limit_from_settings(self):
        max_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
        data = {"limit": str(max_limit)}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["limit"], max_limit)

    def test_get_labels_search_field_strips_whitespace(self):
        data = {"search": "   LabelName   "}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["search"], "LabelName")

    def test_get_labels_search_field_returns_empty_string_for_blank_whitespace(self):
        data = {"search": "     "}
        serializer = GetLabelQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["search"], "")

    def test_get_labels_default_search_value_is_empty_string(self):
        serializer = GetLabelQueryParamsSerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["search"], "")
