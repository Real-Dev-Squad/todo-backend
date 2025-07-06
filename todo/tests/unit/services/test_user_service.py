from unittest import TestCase
from unittest.mock import patch
from rest_framework.exceptions import ValidationError as DRFValidationError

from todo.services.user_service import UserService
from todo.models.user import UserModel
from todo.exceptions.google_auth_exceptions import GoogleUserNotFoundException, GoogleAPIException
from todo.tests.fixtures.user import users_db_data
from todo.constants.messages import ValidationErrors, RepositoryErrors


class UserServiceTests(TestCase):
    def setUp(self) -> None:
        self.valid_google_user_data = users_db_data[0].copy()
        self.valid_google_user_data["email"] = self.valid_google_user_data.pop("email_id")
        self.user_model = UserModel(**users_db_data[0])

    @patch("todo.services.user_service.UserRepository")
    def test_create_or_update_user_success(self, mock_repository):
        mock_repository.create_or_update.return_value = self.user_model

        result = UserService.create_or_update_user(self.valid_google_user_data)

        mock_repository.create_or_update.assert_called_once_with(self.valid_google_user_data)
        self.assertEqual(result, self.user_model)

    @patch("todo.services.user_service.UserRepository")
    def test_create_or_update_user_validation_error(self, mock_repository):
        invalid_data = {"google_id": "123"}

        with self.assertRaises(DRFValidationError) as context:
            UserService.create_or_update_user(invalid_data)
        self.assertIn(ValidationErrors.MISSING_EMAIL, str(context.exception.detail))
        self.assertIn(ValidationErrors.MISSING_NAME, str(context.exception.detail))
        mock_repository.create_or_update.assert_not_called()

    @patch("todo.services.user_service.UserRepository")
    def test_create_or_update_user_repository_error(self, mock_repository):
        mock_repository.create_or_update.side_effect = Exception("Database error")

        with self.assertRaises(GoogleAPIException) as context:
            UserService.create_or_update_user(self.valid_google_user_data)
        self.assertIn(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format("Database error"), str(context.exception))

    @patch("todo.services.user_service.UserRepository")
    def test_get_user_by_id_success(self, mock_repository):
        mock_repository.get_by_id.return_value = self.user_model

        result = UserService.get_user_by_id("123")

        mock_repository.get_by_id.assert_called_once_with("123")
        self.assertEqual(result, self.user_model)

    @patch("todo.services.user_service.UserRepository")
    def test_get_user_by_id_not_found(self, mock_repository):
        mock_repository.get_by_id.return_value = None

        with self.assertRaises(GoogleUserNotFoundException):
            UserService.get_user_by_id("123")
        mock_repository.get_by_id.assert_called_once_with("123")

    def test_validate_google_user_data_success(self):
        try:
            UserService._validate_google_user_data(self.valid_google_user_data)
        except DRFValidationError:
            self.fail("ValidationError raised unexpectedly!")

    def test_validate_google_user_data_missing_fields(self):
        base_data = users_db_data[0].copy()
        base_data["email"] = base_data.pop("email_id")
        test_cases = []
        for missing_key in ["google_id", "email", "name"]:
            case = base_data.copy()
            case.pop(missing_key)
            test_cases.append(case)

        for invalid_data in test_cases:
            with self.subTest(f"Testing missing field in {invalid_data}"):
                with self.assertRaises(DRFValidationError) as context:
                    UserService._validate_google_user_data(invalid_data)

                error_dict = context.exception.detail
                self.assertTrue(len(error_dict) > 0)

                if "google_id" not in invalid_data:
                    self.assertIn(ValidationErrors.MISSING_GOOGLE_ID, str(error_dict))
                if "email" not in invalid_data:
                    self.assertIn(ValidationErrors.MISSING_EMAIL, str(error_dict))
                if "name" not in invalid_data:
                    self.assertIn(ValidationErrors.MISSING_NAME, str(error_dict))
