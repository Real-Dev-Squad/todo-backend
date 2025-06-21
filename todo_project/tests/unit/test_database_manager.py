from unittest import TestCase
from unittest.mock import patch, MagicMock

from django.conf import settings
from todo_project.db.config import DatabaseManager
from pymongo import MongoClient
from pymongo.database import Database, Collection
from pymongo.errors import ConnectionFailure


class DatabaseManagerTests(TestCase):
    def setUp(self):
        DatabaseManager._DatabaseManager__instance = None
        self.database_manager = DatabaseManager()

    def tearDown(self):
        self.database_manager = None

    def test_singleton_ensures_single_instance(self):
        database_manager1 = DatabaseManager()
        database_manager2 = DatabaseManager()
        self.assertIs(database_manager1, database_manager2)

    @patch("todo_project.db.config.MongoClient")
    def test_initializes_db_client_on_first_call(self, mock_mongo_client):
        mock_client_instance = MagicMock(spec=MongoClient)
        mock_mongo_client.return_value = mock_client_instance
        db_client = self.database_manager._get_database_client()

        mock_mongo_client.assert_called_once_with(settings.MONGODB_URI, tz_aware=True)

        self.assertIs(db_client, mock_client_instance)

    @patch("todo_project.db.config.MongoClient")
    def test_reuses_existing_db_client_on_subsequent_calls(self, mock_mongo_client):
        mock_client_instance = MagicMock(spec=MongoClient)
        mock_mongo_client.return_value = mock_client_instance

        db_client1 = self.database_manager._get_database_client()
        db_client2 = self.database_manager._get_database_client()

        mock_mongo_client.assert_called_once()
        self.assertIs(db_client1, db_client2)

    @patch("todo_project.db.config.DatabaseManager._get_database_client")
    def test_initializes_db_on_first_call(self, mock_get_database_client):
        mock_client = MagicMock(spec=MongoClient)
        mock_database_instance = MagicMock(spec=Database)
        mock_client.__getitem__.return_value = mock_database_instance
        mock_get_database_client.return_value = mock_client

        db_instance = self.database_manager.get_database()

        mock_get_database_client.assert_called_once()

        mock_client.__getitem__.assert_called_once_with(settings.DB_NAME)

        self.assertIs(db_instance, mock_database_instance)

    @patch("todo_project.db.config.DatabaseManager._get_database_client")
    def test_reuses_existing_db_on_subsequent_calls(self, mock_get_database_client):
        mock_client = MagicMock(spec=MongoClient)
        mock_database_instance = MagicMock(spec=Database)
        mock_client.__getitem__.return_value = mock_database_instance
        mock_get_database_client.return_value = mock_client

        db_instance1 = self.database_manager.get_database()
        db_instance2 = self.database_manager.get_database()

        mock_get_database_client.assert_called_once()

        self.assertIs(db_instance1, db_instance2)

    @patch("todo_project.db.config.DatabaseManager.get_database")
    def test_get_collection_returns_specified_collection(self, mock_get_database):
        mock_database_instance = MagicMock(spec=Database)
        mock_collection = MagicMock(spec=Collection)
        mock_database_instance.__getitem__.return_value = mock_collection
        mock_get_database.return_value = mock_database_instance

        collection_name = "test_collection"
        collection = self.database_manager.get_collection(collection_name)

        self.assertEqual(collection, mock_collection)
        mock_database_instance.__getitem__.assert_called_once_with(collection_name)

    @patch("todo_project.db.config.DatabaseManager._get_database_client")
    def test_check_db_health_returns_true_on_successful_connection(self, mock_get_database_client):
        mock_client = MagicMock()
        mock_client.admin.command.return_value = {"ok": 1}
        mock_get_database_client.return_value = mock_client

        result = self.database_manager.check_database_health()

        self.assertTrue(result)
        mock_get_database_client.assert_called_once()
        mock_client.admin.command.assert_called_once_with("ping")

    @patch("todo_project.db.config.DatabaseManager._get_database_client")
    def test_check_db_health_returns_false_on_connection_failure(self, mock_get_database_client):
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = ConnectionFailure("Mocked connection failure")
        mock_get_database_client.return_value = mock_client

        result = self.database_manager.check_database_health()

        self.assertFalse(result)
        mock_get_database_client.assert_called_once()
        mock_client.admin.command.assert_called_once_with("ping")
