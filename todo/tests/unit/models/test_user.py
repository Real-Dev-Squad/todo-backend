from unittest import TestCase
from datetime import datetime, timezone
from pydantic_core._pydantic_core import ValidationError
from todo.models.user import UserModel
from todo.tests.fixtures.user import users_db_data


class UserModelTest(TestCase):
    def setUp(self) -> None:
        self.valid_user_data = users_db_data[0]

    def test_user_model_instantiates_with_valid_data(self):
        user = UserModel(**self.valid_user_data)

        self.assertEqual(user.google_id, self.valid_user_data["google_id"])
        self.assertEqual(user.email_id, self.valid_user_data["email_id"])
        self.assertEqual(user.name, self.valid_user_data["name"])
        self.assertEqual(user.created_at, self.valid_user_data["created_at"])
        self.assertEqual(user.updated_at, self.valid_user_data["updated_at"])

    def test_user_model_throws_error_when_missing_required_fields(self):
        required_fields = ["google_id", "email_id", "name"]

        for field in required_fields:
            with self.subTest(f"missing field: {field}"):
                incomplete_data = self.valid_user_data.copy()
                incomplete_data.pop(field, None)

                with self.assertRaises(ValidationError) as context:
                    UserModel(**incomplete_data)

                error_fields = [e["loc"][0] for e in context.exception.errors()]
                self.assertIn(field, error_fields)

    def test_user_model_throws_error_when_invalid_email(self):
        invalid_data = self.valid_user_data.copy()
        invalid_data["email_id"] = "invalid-email"

        with self.assertRaises(ValidationError) as context:
            UserModel(**invalid_data)

        error_fields = [e["loc"][0] for e in context.exception.errors()]
        self.assertIn("email_id", error_fields)

    def test_user_model_sets_default_timestamps(self):
        minimal_data = {
            "google_id": self.valid_user_data["google_id"],
            "email_id": self.valid_user_data["email_id"],
            "name": self.valid_user_data["name"],
        }
        user = UserModel(**minimal_data)

        self.assertIsInstance(user.created_at, datetime)
        self.assertIsNone(user.updated_at)
        self.assertLessEqual(user.created_at, datetime.now(timezone.utc))
