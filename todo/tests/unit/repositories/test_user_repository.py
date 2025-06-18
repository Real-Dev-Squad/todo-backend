from unittest import TestCase
from unittest.mock import patch, MagicMock
from bson import ObjectId

from todo.repositories.user_repository import UserRepository
from todo.models.user import UserModel
from todo.models.common.pyobjectid import PyObjectId
from todo.exceptions.google_auth_exceptions import GoogleUserNotFoundException, GoogleAPIException
from todo.tests.fixtures.user import users_db_data
from todo.constants.messages import RepositoryErrors


class UserRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.valid_user_data = {"google_id": "123456789", "email": "test@example.com", "name": "Test User"}
        self.user_model = UserModel(**users_db_data[0])
        self.mock_collection = MagicMock()
        self.mock_db_manager = MagicMock()
        self.mock_db_manager.get_collection.return_value = self.mock_collection

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_get_by_id_success(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        user_id = str(ObjectId())
        self.mock_collection.find_one.return_value = users_db_data[0]

        result = UserRepository.get_by_id(user_id)

        self.mock_collection.find_one.assert_called_once_with({"_id": PyObjectId(user_id)})
        self.assertIsInstance(result, UserModel)
        self.assertEqual(result.google_id, users_db_data[0]["google_id"])

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_get_by_id_not_found(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        user_id = str(ObjectId())
        self.mock_collection.find_one.return_value = None

        result = UserRepository.get_by_id(user_id)
        self.assertIsNone(result)

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_get_by_id_database_error(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        user_id = str(ObjectId())
        self.mock_collection.find_one.side_effect = Exception("Database error")

        with self.assertRaises(GoogleUserNotFoundException):
            UserRepository.get_by_id(user_id)

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_create_or_update_success(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        self.mock_collection.find_one_and_update.return_value = users_db_data[0]

        result = UserRepository.create_or_update(self.valid_user_data)

        self.mock_collection.find_one_and_update.assert_called_once()
        call_args = self.mock_collection.find_one_and_update.call_args[0]
        self.assertEqual(call_args[0], {"google_id": self.valid_user_data["google_id"]})
        self.assertIsInstance(result, UserModel)
        self.assertEqual(result.google_id, users_db_data[0]["google_id"])

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_create_or_update_no_result(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        self.mock_collection.find_one_and_update.return_value = None

        with self.assertRaises(GoogleAPIException) as context:
            UserRepository.create_or_update(self.valid_user_data)
        self.assertIn(RepositoryErrors.USER_OPERATION_FAILED, str(context.exception))

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_create_or_update_database_error(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        self.mock_collection.find_one_and_update.side_effect = Exception("Database error")

        with self.assertRaises(GoogleAPIException) as context:
            UserRepository.create_or_update(self.valid_user_data)
        self.assertIn(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format("Database error"), str(context.exception))

    @patch("todo.repositories.user_repository.DatabaseManager")
    def test_create_or_update_sets_timestamps(self, mock_db_manager):
        mock_db_manager.return_value = self.mock_db_manager
        self.mock_collection.find_one_and_update.return_value = users_db_data[0]

        UserRepository.create_or_update(self.valid_user_data)

        call_args = self.mock_collection.find_one_and_update.call_args[0]
        update_doc = call_args[1]
        self.assertIn("$set", update_doc)
        self.assertIn("updated_at", update_doc["$set"])
        self.assertIn("$setOnInsert", update_doc)
        self.assertIn("created_at", update_doc["$setOnInsert"])
