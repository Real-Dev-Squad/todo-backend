from unittest import TestCase
from unittest.mock import patch, MagicMock
from pymongo.collection import Collection
from todo.models.task import TaskModel
from todo.repositories.task_repository import TaskRepository
from todo.tests.fixtures.task import tasks_db_data


class TaskRepositoryTests(TestCase):
    def setUp(self):
        self.task_data = tasks_db_data

        self.patcher_get_collection = patch("todo.repositories.task_repository.TaskRepository.get_collection")
        self.mock_get_collection = self.patcher_get_collection.start()
        self.mock_collection = MagicMock(spec=Collection)
        self.mock_get_collection.return_value = self.mock_collection

    def tearDown(self):
        self.patcher_get_collection.stop()

    def test_list_applies_pagination_correctly(self):
        self.mock_collection.find.return_value.skip.return_value.limit.return_value = self.task_data

        page = 1
        limit = 10
        result = TaskRepository.list(page, limit)

        self.assertEqual(len(result), len(self.task_data))
        self.assertTrue(all(isinstance(task, TaskModel) for task in result))

        self.mock_collection.find.assert_called_once()
        self.mock_collection.find.return_value.skip.assert_called_once_with(0)
        self.mock_collection.find.return_value.skip.return_value.limit.assert_called_once_with(limit)

    def test_list_returns_empty_list_for_no_tasks(self):
        self.mock_collection.find.return_value.skip.return_value.limit.return_value = []

        result = TaskRepository.list(2, 10)

        self.assertEqual(result, [])
        self.mock_collection.find.assert_called_once()
        self.mock_collection.find.return_value.skip.assert_called_once_with(10)
        self.mock_collection.find.return_value.skip.return_value.limit.assert_called_once_with(10)

    def test_count_returns_total_task_count(self):
        self.mock_collection.count_documents.return_value = 42

        result = TaskRepository.count()

        self.assertEqual(result, 42)
        self.mock_collection.count_documents.assert_called_once_with({})
        
    def test_get_all_returns_all_tasks(self):
        self.mock_collection.find.return_value = self.task_data
        
        result = TaskRepository.get_all()
        
        self.assertEqual(len(result), len(self.task_data))
        self.assertTrue(all(isinstance(task, TaskModel) for task in result))
        
        self.mock_collection.find.assert_called_once()
        
    def test_get_all_returns_empty_list_for_no_tasks(self):
        self.mock_collection.find.return_value = []
        
        result = TaskRepository.get_all()
        
        self.assertEqual(result, [])
        self.mock_collection.find.assert_called_once()