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
        incomplete_data = self.valid_task_data.copy()
        required_fields = ["title", "createdAt", "createdBy"]
        for field_name in required_fields:
            del incomplete_data[field_name]

        with self.assertRaises(ValidationError) as context:
            TaskModel(**incomplete_data)

        missing_fields_count = 0
        for error in context.exception.errors():
            self.assertEqual(error.get("type"), "missing")
            self.assertIn(error.get("loc")[0], required_fields)
            missing_fields_count += 1
        self.assertEqual(missing_fields_count, len(required_fields))

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
