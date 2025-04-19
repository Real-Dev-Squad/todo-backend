# todo/tests/integration/db/test_task_repository_integration.py
from unittest import TestCase
from datetime import datetime, timezone

from todo.models.task import TaskModel
from todo.constants.task import TaskPriority, TaskStatus
from todo.repositories.task_repository import TaskRepository


class TaskResponseIntegrationTests(TestCase):
    def setUp(self):
        try:
            client = TaskRepository.get_client()
            db = client.get_database()
            db.counters.delete_many({"_id": "taskDisplayId"})
            db.tasks.delete_many({"title": {"$regex": "^Integration Test"}})
        except Exception as e:
            print(f"Warning: MongoDB not available: {str(e)}. Some tests may fail.")

        self.task = TaskModel(
            title="Integration Repo Test",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
            labels=[],  # Explicitly set empty labels
        )

    def test_task_count_reflects_new_inserts(self):
        initial_count = TaskRepository.count()
        TaskRepository.create(self.task)
        self.assertEqual(TaskRepository.count(), initial_count + 1)

    def test_sequential_display_ids(self):
        """Test that displayIds are sequential and don't have gaps"""
        # Create first task
        task1 = TaskModel(
            title="Integration Test First",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
            labels=[],
        )
        created_task1 = TaskRepository.create(task1)

        # Create second task
        task2 = TaskModel(
            title="Integration Test Second",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.IN_PROGRESS,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
            labels=[],
        )
        created_task2 = TaskRepository.create(task2)

        # Check sequential IDs
        id1 = int(created_task1.displayId.lstrip("#"))
        id2 = int(created_task2.displayId.lstrip("#"))
        self.assertEqual(id2, id1 + 1, "Task displayIds should be sequential")
