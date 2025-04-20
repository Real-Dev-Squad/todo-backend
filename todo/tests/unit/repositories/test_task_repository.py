from unittest import TestCase
from unittest.mock import patch, MagicMock
from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime, timezone

from todo.models.task import TaskModel
from todo.repositories.task_repository import TaskRepository
from todo.constants.task import TaskPriority, TaskStatus
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

    @patch("todo.repositories.task_repository.TaskRepository.get_collection")
    @patch("todo.repositories.task_repository.TaskRepository.get_client")
    def test_create_task_successfully_inserts_and_returns_task(self, mock_get_client, mock_get_collection):
        mock_session = MagicMock()
        mock_get_client.return_value.start_session.return_value.__enter__.return_value = mock_session

        mock_db = MagicMock()
        mock_get_client.return_value.get_database.return_value = mock_db

        mock_counter_result = {"_id": "taskDisplayId", "seq": 42}
        mock_db.counters.find_one_and_update.return_value = mock_counter_result

        mock_collection = MagicMock()
        inserted_id = ObjectId()
        mock_collection.insert_one.return_value.inserted_id = inserted_id
        mock_get_collection.return_value = mock_collection

        task = TaskModel(
            title="Happy path task",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

        created_task = TaskRepository.create(task)

        self.assertEqual(created_task.displayId, f"#{mock_counter_result['seq']}")
        self.assertEqual(created_task.id, inserted_id)
        self.assertIsNotNone(created_task.createdAt)

        mock_db.counters.find_one_and_update.assert_called_once()
        mock_collection.insert_one.assert_called_once()

    @patch("todo.repositories.task_repository.TaskRepository.get_client")
    @patch("todo.repositories.task_repository.TaskRepository.get_collection")
    def test_create_task_creates_counter_if_not_exists(self, mock_get_collection, mock_get_client):
        mock_session = MagicMock()
        mock_get_client.return_value.start_session.return_value.__enter__.return_value = mock_session

        mock_db = MagicMock()
        mock_get_client.return_value.get_database.return_value = mock_db

        mock_db.counters.find_one_and_update.return_value = None

        mock_collection = MagicMock()
        inserted_id = ObjectId()
        mock_collection.insert_one.return_value.inserted_id = inserted_id
        mock_get_collection.return_value = mock_collection

        task = TaskModel(
            title="First task with no counter",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

        created_task = TaskRepository.create(task)

        mock_db.counters.insert_one.assert_called_once_with({"_id": "taskDisplayId", "seq": 1}, session=mock_session)

        self.assertEqual(created_task.displayId, "#1")
        self.assertEqual(created_task.id, inserted_id)

    @patch("todo.repositories.task_repository.TaskRepository.get_client")
    @patch("todo.repositories.task_repository.TaskRepository.get_collection")
    def test_create_task_handles_exception(self, mock_get_collection, mock_get_client):
        mock_session = MagicMock()
        mock_get_client.return_value.start_session.return_value.__enter__.return_value = mock_session

        mock_db = MagicMock()
        mock_get_client.return_value.get_database.return_value = mock_db
        mock_db.counters.find_one_and_update.side_effect = Exception("Database error")

        task = TaskModel(
            title="Task that will fail",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

        with self.assertRaises(ValueError) as context:
            TaskRepository.create(task)

        self.assertIn("Failed to create task", str(context.exception))
