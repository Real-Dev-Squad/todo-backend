import unittest
from unittest.mock import patch, MagicMock
from bson import ObjectId
from pymongo import ReturnDocument
from todo.repositories.task_repository import TaskRepository
from todo.models.task import TaskModel
from todo.tests.fixtures.task import tasks_db_data


class TestDeleteTaskById(unittest.TestCase):
    def setUp(self):
        self.task_id = tasks_db_data[0]["id"]
        self.mock_task_data = tasks_db_data[0]

    @patch("todo.repositories.task_repository.TaskRepository.get_collection")
    def test_delete_task_success_when_isDeleted_false(self, mock_get_collection):
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.find_one_and_update.return_value = self.mock_task_data

        result = TaskRepository.delete_by_id(self.task_id)

        self.assertIsInstance(result, TaskModel)
        self.assertEqual(result.title, tasks_db_data[0]["title"])
        mock_collection.find_one_and_update.assert_called_once_with(
            {
                "_id": ObjectId(self.task_id),
                "$or": [{"isDeleted": False}, {"isDeleted": {"$exists": False}}],
            },
            {"$set": {"isDeleted": True}},
            return_document=ReturnDocument.AFTER,
        )

    @patch("todo.repositories.task_repository.TaskRepository.get_collection")
    def test_delete_task_success_when_isDeleted_missing(self, mock_get_collection):
        mock_data = self.mock_task_data.copy()
        mock_data.pop("isDeleted")

        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.find_one_and_update.return_value = mock_data

        result = TaskRepository.delete_by_id(self.task_id)
        self.assertIsInstance(result, TaskModel)

    @patch("todo.repositories.task_repository.TaskRepository.get_collection")
    def test_delete_task_returns_none_when_already_deleted(self, mock_get_collection):
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.find_one_and_update.return_value = None

        result = TaskRepository.delete_by_id(self.task_id)
        self.assertIsNone(result)

    def test_delete_task_invalid_object_id_raises_exception(self):
        invalid_id = "not-valid-id"
        with self.assertRaises(Exception):
            TaskRepository.delete_by_id(invalid_id)
