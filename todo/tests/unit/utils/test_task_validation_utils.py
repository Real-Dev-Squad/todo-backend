from unittest.mock import patch, MagicMock
from django.test import TestCase
from bson import ObjectId

from todo.utils.task_validation_utils import validate_task_exists
from todo.models.task import TaskModel
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse


class TestTaskValidationUtils(TestCase):
    def test_validate_task_exists_success(self):
        """Test successful task validation when task exists"""
        task_id = str(ObjectId())
        mock_task = MagicMock(spec=TaskModel)

        with patch("todo.utils.task_validation_utils.TaskRepository.get_by_id", return_value=mock_task):
            result = validate_task_exists(task_id)
            self.assertEqual(result, mock_task)

    def test_validate_task_exists_invalid_object_id(self):
        """Test validation fails with invalid ObjectId format"""
        invalid_task_id = "invalid-id"

        with self.assertRaises(ValueError) as context:
            validate_task_exists(invalid_task_id)
        
        error_response = context.exception.args[0]
        self.assertIsInstance(error_response, ApiErrorResponse)
        self.assertEqual(error_response.statusCode, 400)
        self.assertEqual(error_response.message, ApiErrors.INVALID_TASK_ID)

    def test_validate_task_exists_task_not_found(self):
        """Test validation fails when task doesn't exist"""
        task_id = str(ObjectId())

        with patch("todo.utils.task_validation_utils.TaskRepository.get_by_id", return_value=None):
            with self.assertRaises(ValueError) as context:
                validate_task_exists(task_id)

        error_response = context.exception.args[0]
        self.assertIsInstance(error_response, ApiErrorResponse)
        self.assertEqual(error_response.statusCode, 404)
        self.assertEqual(error_response.message, ApiErrors.TASK_NOT_FOUND.format(task_id))
