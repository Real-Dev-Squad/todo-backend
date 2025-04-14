from unittest import TestCase

from pydantic_core._pydantic_core import ValidationError
from todo.models.task import TaskModel
from todo.constants.task import TaskPriority, TaskStatus
from todo.tests.fixtures.task import tasks_db_data


class TaskModelTest(TestCase):
    def setUp(self):
        self.valid_task_data = tasks_db_data[0]

    def test_task_model_instantiates_with_valid_data(self):
        task = TaskModel(**self.valid_task_data)

        self.assertEqual(task.priority, TaskPriority.HIGH)  # Enum value
        self.assertEqual(task.status, TaskStatus.TODO)  # Enum value
        self.assertFalse(task.isDeleted)  # Default value

    def test_task_model_throws_error_when_missing_required_fields(self):
        required_fields = ["title", "createdAt", "createdBy"]

        for field in required_fields:
            with self.subTest(f"missing field: {field}"):
                incomplete_data = self.valid_task_data.copy()
                incomplete_data.pop(field, None)

                with self.assertRaises(ValidationError) as context:
                    TaskModel(**incomplete_data)

                error_fields = [e["loc"][0] for e in context.exception.errors()]
                self.assertIn(field, error_fields)

    def test_task_model_throws_error_when_invalid_enum_value(self):
        invalid_data = self.valid_task_data.copy()
        invalid_data["priority"] = "INVALID_PRIORITY"
        invalid_data["status"] = "INVALID_STATUS"

        with self.assertRaises(ValidationError) as context:
            TaskModel(**invalid_data)
        invalid_field_names = []
        for error in context.exception.errors():
            invalid_field_names.append(error.get("loc")[0])
        self.assertEqual(invalid_field_names, ["priority", "status"])

    def test_task_model_defaults_are_set_correctly(self):
        minimal_data = {
            "title": "Minimal Task",
            "createdAt": self.valid_task_data["createdAt"],
            "createdBy": self.valid_task_data["createdBy"],
        }
        task = TaskModel(**minimal_data)

        self.assertEqual(task.priority, TaskPriority.LOW)
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertFalse(task.isAcknowledged)
        self.assertFalse(task.isDeleted)

    def test_task_model_allows_none_for_optional_fields(self):
        data = self.valid_task_data.copy()
        optional_fields = ["description", "assignee", "labels", "dueAt", "updatedBy", "updatedAt", "deferredDetails"]

        for field in optional_fields:
            data[field] = None

        task = TaskModel(**data)
        self.assertIsNone(task.description)
        self.assertIsNone(task.assignee)
        self.assertIsNone(task.dueAt)
