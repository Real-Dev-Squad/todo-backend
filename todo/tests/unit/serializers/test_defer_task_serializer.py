from unittest import TestCase
from rest_framework.exceptions import ValidationError
from datetime import datetime, timedelta, timezone

from todo.serializers.defer_task_serializer import DeferTaskSerializer


class DeferTaskSerializerTests(TestCase):
    def test_serializer_with_valid_future_date(self):
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        data = {"deferredTill": future_date}
        serializer = DeferTaskSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertEqual(serializer.validated_data["deferredTill"], future_date)

    def test_serializer_with_past_date_raises_validation_error(self):
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        data = {"deferredTill": past_date}
        serializer = DeferTaskSerializer(data=data)
        with self.assertRaises(ValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn("deferredTill cannot be in the past.", str(cm.exception.detail))

    def test_serializer_with_invalid_data_type_raises_validation_error(self):
        data = {"deferredTill": "not-a-date"}
        serializer = DeferTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("deferredTill", serializer.errors)
        self.assertIn("Datetime has wrong format", str(serializer.errors["deferredTill"]))

    def test_serializer_with_missing_field_raises_validation_error(self):
        data = {}
        serializer = DeferTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("deferredTill", serializer.errors)
        self.assertIn("This field is required.", str(serializer.errors["deferredTill"]))
