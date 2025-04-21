from unittest import TestCase
from unittest.mock import MagicMock, patch
from todo.repositories.common.mongo_repository import MongoRepository
from todo_project.db.config import DatabaseManager


class MongoRepositoryTests(TestCase):
    def test_subclass_without_collection_name_raises_error(self):
        with self.assertRaises(TypeError) as context:

            class InvalidRepository(MongoRepository):
                pass

        self.assertIn(
            "Class InvalidRepository must define a static `collection_name` field as a string.", str(context.exception)
        )

    def test_subclass_with_invalid_collection_name_raises_error(self):
        with self.assertRaises(TypeError) as context:

            class InvalidRepository(MongoRepository):
                collection_name = 123

        self.assertIn(
            "Class InvalidRepository must define a static `collection_name` field as a string.", str(context.exception)
        )

    def test_subclass_with_valid_collection_name_passes(self):
        try:

            class ValidRepository(MongoRepository):
                collection_name = "valid_collection"
        except TypeError:
            self.fail("TypeError raised for a valid subclass with collection_name")

    @patch.object(DatabaseManager, "get_collection")
    def test_get_collection_initializes_collection(self, mock_get_collection):
        class TestRepository(MongoRepository):
            collection_name = "test_collection"

        mock_get_collection.return_value = MagicMock()

        collection = TestRepository.get_collection()
        mock_get_collection.assert_called_once_with("test_collection")
        self.assertEqual(TestRepository.collection, collection)

    @patch.object(DatabaseManager, "get_collection")
    def test_get_collection_uses_cached_collection(self, mock_get_collection):
        class TestRepository(MongoRepository):
            collection_name = "test_collection"

        mock_get_collection.return_value = MagicMock()

        TestRepository.get_collection()
        TestRepository.get_collection()

        mock_get_collection.assert_called_once_with("test_collection")
