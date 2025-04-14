from unittest import TestCase
from datetime import datetime, timezone

from todo.models.task import TaskModel
from todo.constants.task import TaskPriority, TaskStatus
from todo.repositories.task_repository import TaskRepository


class TaskResponseIntegrationTests(TestCase):
    def setUp(self):
        self.task = TaskModel(
            title="Integration Repo Test",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            createdAt=datetime.now(timezone.utc),
            createdBy="system",
        )

    def test_task_count_reflects_new_inserts(self):
        initial_count = TaskRepository.count()
        TaskRepository.create(self.task)
        self.assertEqual(TaskRepository.count(), initial_count + 1)
