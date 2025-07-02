from unittest import TestCase
from datetime import datetime

from todo.models.label import LabelModel
from todo.tests.fixtures.label import label_db_data
from pydantic_core._pydantic_core import ValidationError


class LabelModelTest(TestCase):
    def setUp(self):
        self.created_at = datetime.now()
        self.valid_data = label_db_data[0]

    def test_label_model_instantiates_with_valid_data(self):
        label = LabelModel(**self.valid_data)
        self.assertFalse(label.isDeleted)  # Default value
        self.assertIsNone(label.updatedAt)  # Default value
        self.assertIsNone(label.updatedBy)  # Default value
        if "_id" in self.valid_data:
            self.assertIsNotNone(label.id)
        else:
            self.assertIsNone(label.id)

    def test_lable_model_throws_error_when_missing_required_fields(self):
        incomplete_data = self.valid_data.copy()
        required_fields = ["name", "color", "createdAt", "createdBy"]
        for field_name in required_fields:
            del incomplete_data[field_name]
        with self.assertRaises(ValidationError) as context:
            LabelModel(**incomplete_data)

        missing_fields_count = 0
        for error in context.exception.errors():
            self.assertEqual(error.get("type"), "missing")
            self.assertIn(error.get("loc")[0], required_fields)
            missing_fields_count += 1
        self.assertEqual(missing_fields_count, len(required_fields))
