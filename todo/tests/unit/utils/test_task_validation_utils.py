import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId

from todo.utils.task_validation_utils import validate_task_exists
from todo.models.task import TaskModel
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse


class TestTaskValidationUtils:
    def test_validate_task_exists_success(self):
        """Test successful task validation when task exists"""
        task_id = str(ObjectId())
        mock_task = MagicMock(spec=TaskModel)

        with patch("todo.utils.task_validation_utils.TaskRepository.get_by_id", return_value=mock_task):
            result = validate_task_exists(task_id)
            assert result == mock_task

    def test_validate_task_exists_invalid_object_id(self):
        """Test validation fails with invalid ObjectId format"""
        invalid_task_id = "invalid-id"

        with pytest.raises(ValueError) as exc_info:
            validate_task_exists(invalid_task_id)

        error_response = exc_info.value.args[0]
        assert isinstance(error_response, ApiErrorResponse)
        assert error_response.statusCode == 400
        assert error_response.message == ApiErrors.INVALID_TASK_ID

    def test_validate_task_exists_task_not_found(self):
        """Test validation fails when task doesn't exist"""
        task_id = str(ObjectId())

        with patch("todo.utils.task_validation_utils.TaskRepository.get_by_id", return_value=None):
            with pytest.raises(ValueError) as exc_info:
                validate_task_exists(task_id)

        error_response = exc_info.value.args[0]
        assert isinstance(error_response, ApiErrorResponse)
        assert error_response.statusCode == 404
        assert error_response.message == ApiErrors.TASK_NOT_FOUND.format(task_id)
