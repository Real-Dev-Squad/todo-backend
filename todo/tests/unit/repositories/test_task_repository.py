from unittest import TestCase
from unittest.mock import patch, MagicMock
from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime, timezone

from todo.models.task import TaskModel
from todo.repositories.task_repository import TaskRepository
from todo.constants.task import TaskPriority, TaskStatus
from todo.tests.fixtures.task import tasks_db_data
from todo.constants.messages import RepositoryErrors


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


class TaskRepositoryCreateTests(TestCase):
    def setUp(self):
        self.task = TaskModel(
            title="Test Task",
            description="Sample",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            assignee="user123",
            labels=[],
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

    @patch("todo.repositories.task_repository.TaskRepository.create")
    def test_create_task_successfully_inserts_and_returns_task(self, mock_create):
        task = TaskModel(
            title="Happy path task",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

        expected_task = task.model_copy(deep=True)
        expected_task.id = ObjectId()
        expected_task.displayId = "#42"

        mock_create.return_value = expected_task

        result = TaskRepository.create(task)

        self.assertEqual(result, expected_task)
        self.assertEqual(result.id, expected_task.id)
        self.assertEqual(result.displayId, "#42")
        mock_create.assert_called_once_with(task)

    @patch("todo.repositories.task_repository.TaskRepository.create")
    def test_create_task_creates_counter_if_not_exists(self, mock_create):
        task = TaskModel(
            title="First task with no counter",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

        expected_task = task.model_copy(deep=True)
        expected_task.id = ObjectId()
        expected_task.displayId = "#1"

        mock_create.return_value = expected_task

        result = TaskRepository.create(task)

        self.assertEqual(result, expected_task)
        self.assertEqual(result.id, expected_task.id)
        self.assertEqual(result.displayId, "#1")
        mock_create.assert_called_once_with(task)

    @patch("todo.repositories.task_repository.TaskRepository.create")
    def test_create_task_handles_exception(self, mock_create):
        task = TaskModel(
            title="Task that will fail",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

        mock_create.side_effect = ValueError(RepositoryErrors.TASK_CREATION_FAILED.format("Database error"))

        with self.assertRaises(ValueError) as context:
            TaskRepository.create(task)

        self.assertIn("Failed to create task", str(context.exception))
        mock_create.assert_called_once_with(task)
