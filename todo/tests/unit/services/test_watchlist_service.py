import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId
from django.test import TestCase, override_settings

from todo.services.watchlist_service import WatchlistService
from todo.dto.watchlist_dto import CreateWatchlistDTO
from todo.models.task import TaskModel
from todo.models.watchlist import WatchlistModel
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_PAGINATION_SETTINGS": {
            "DEFAULT_PAGE_LIMIT": 10,
            "MAX_PAGE_LIMIT": 100
        }
    }
)
class TestWatchlistService(TestCase):
    def test_add_task_success(self):
        """Test successful task addition to watchlist"""
        task_id = str(ObjectId())
        user_id = str(ObjectId())
        created_by = str(ObjectId())
        
        mock_task = MagicMock(spec=TaskModel)
        mock_watchlist = MagicMock(spec=WatchlistModel)
        mock_watchlist.taskId = task_id
        mock_watchlist.userId = user_id
        mock_watchlist.createdBy = created_by
        mock_watchlist.createdAt = datetime.now(timezone.utc)
        
        dto = CreateWatchlistDTO(
            taskId=task_id,
            userId=user_id,
            createdBy=created_by,
            createdAt=datetime.now(timezone.utc)
        )
        
        with patch('todo.services.watchlist_service.validate_task_exists', return_value=mock_task), \
             patch('todo.services.watchlist_service.WatchlistRepository.get_by_user_and_task', return_value=None), \
             patch('todo.services.watchlist_service.WatchlistRepository.create', return_value=mock_watchlist):
            
            result = WatchlistService.add_task(dto)
            assert result.data.taskId == task_id
            assert result.data.userId == user_id
            assert result.data.createdBy == created_by

    def test_add_task_validation_fails_invalid_task_id(self):
        """Test that validation fails with invalid task ID"""
        task_id = "invalid-id"
        user_id = str(ObjectId())
        created_by = str(ObjectId())
        
        dto = CreateWatchlistDTO(
            taskId=task_id,
            userId=user_id,
            createdBy=created_by,
            createdAt=datetime.now(timezone.utc)
        )
        
        error_response = ApiErrorResponse(
            statusCode=400,
            message=ApiErrors.INVALID_TASK_ID,
            errors=[]
        )
        
        with patch('todo.services.watchlist_service.validate_task_exists', side_effect=ValueError(error_response)):
            with pytest.raises(ValueError) as exc_info:
                WatchlistService.add_task(dto)
            
            assert exc_info.value.args[0] == error_response

    def test_add_task_validation_fails_task_not_found(self):
        """Test that validation fails when task doesn't exist"""
        task_id = str(ObjectId())
        user_id = str(ObjectId())
        created_by = str(ObjectId())
        
        dto = CreateWatchlistDTO(
            taskId=task_id,
            userId=user_id,
            createdBy=created_by,
            createdAt=datetime.now(timezone.utc)
        )
        
        error_response = ApiErrorResponse(
            statusCode=404,
            message=ApiErrors.TASK_NOT_FOUND.format(task_id),
            errors=[]
        )
        
        with patch('todo.services.watchlist_service.validate_task_exists', side_effect=ValueError(error_response)):
            with pytest.raises(ValueError) as exc_info:
                WatchlistService.add_task(dto)
            
            assert exc_info.value.args[0] == error_response

    def test_update_task_validation_fails_invalid_task_id(self):
        """Test that update validation fails with invalid task ID"""
        task_id = ObjectId()
        user_id = ObjectId()
        dto = {"isActive": True}
        
        error_response = ApiErrorResponse(
            statusCode=400,
            message=ApiErrors.INVALID_TASK_ID,
            errors=[]
        )
        
        with patch('todo.services.watchlist_service.validate_task_exists', side_effect=ValueError(error_response)):
            with pytest.raises(ValueError) as exc_info:
                WatchlistService.update_task(task_id, dto, user_id)
            
            assert exc_info.value.args[0] == error_response 