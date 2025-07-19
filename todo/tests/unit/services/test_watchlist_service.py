from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId
from django.test import TestCase, override_settings

from todo.services.watchlist_service import WatchlistService
from todo.dto.watchlist_dto import CreateWatchlistDTO, WatchlistDTO, AssigneeDTO
from todo.models.task import TaskModel
from todo.models.watchlist import WatchlistModel
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse
from todo.dto.responses.get_watchlist_task_response import GetWatchlistTasksResponse


@override_settings(REST_FRAMEWORK={"DEFAULT_PAGINATION_SETTINGS": {"DEFAULT_PAGE_LIMIT": 10, "MAX_PAGE_LIMIT": 100}})
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
            taskId=task_id, userId=user_id, createdBy=created_by, createdAt=datetime.now(timezone.utc)
        )

        with (
            patch("todo.services.watchlist_service.validate_task_exists", return_value=mock_task),
            patch("todo.services.watchlist_service.WatchlistRepository.get_by_user_and_task", return_value=None),
            patch("todo.services.watchlist_service.WatchlistRepository.create", return_value=mock_watchlist),
        ):
            result = WatchlistService.add_task(dto)
            self.assertEqual(result.data.taskId, task_id)
            self.assertEqual(result.data.userId, user_id)
            self.assertEqual(result.data.createdBy, created_by)

    def test_get_watchlisted_tasks_with_assignee(self):
        """Test getting watchlisted tasks with assignee details (who the task belongs to)"""
        user_id = str(ObjectId())
        task_id = str(ObjectId())
        assignee_id = str(ObjectId())
        
        # Create mock assignee data (who the task belongs to)
        assignee_dto = AssigneeDTO(
            id=assignee_id,
            name="John Doe",
            email="john@example.com",
            type="user"
        )
        
        # Create mock watchlist task with assignee
        mock_watchlist_task = WatchlistDTO(
            taskId=task_id,
            displayId="TASK-001",
            title="Test Task",
            description="Test Description",
            priority=None,
            status=None,
            isAcknowledged=False,
            isDeleted=False,
            labels=[],
            dueAt=None,
            createdAt=datetime.now(timezone.utc),
            createdBy=user_id,
            watchlistId=str(ObjectId()),
            assignee=assignee_dto
        )

        with patch("todo.services.watchlist_service.WatchlistRepository.get_watchlisted_tasks") as mock_get:
            mock_get.return_value = (1, [mock_watchlist_task])
            
            result = WatchlistService.get_watchlisted_tasks(page=1, limit=10, user_id=user_id)
            
            self.assertIsInstance(result, GetWatchlistTasksResponse)
            self.assertEqual(len(result.tasks), 1)
            self.assertEqual(result.tasks[0].taskId, task_id)
            self.assertEqual(result.tasks[0].title, "Test Task")
            
            # Verify assignee details are included (who the task belongs to)
            self.assertIsNotNone(result.tasks[0].assignee)
            self.assertEqual(result.tasks[0].assignee.id, assignee_id)
            self.assertEqual(result.tasks[0].assignee.name, "John Doe")
            self.assertEqual(result.tasks[0].assignee.email, "john@example.com")
            self.assertEqual(result.tasks[0].assignee.type, "user")

    def test_get_watchlisted_tasks_without_assignee(self):
        """Test getting watchlisted tasks without assignee details (unassigned task)"""
        user_id = str(ObjectId())
        task_id = str(ObjectId())
        
        # Create mock watchlist task without assignee (unassigned task)
        mock_watchlist_task = WatchlistDTO(
            taskId=task_id,
            displayId="TASK-002",
            title="Unassigned Task",
            description="Task without assignee",
            priority=None,
            status=None,
            isAcknowledged=False,
            isDeleted=False,
            labels=[],
            dueAt=None,
            createdAt=datetime.now(timezone.utc),
            createdBy=user_id,
            watchlistId=str(ObjectId()),
            assignee=None
        )

        with patch("todo.services.watchlist_service.WatchlistRepository.get_watchlisted_tasks") as mock_get:
            mock_get.return_value = (1, [mock_watchlist_task])
            
            result = WatchlistService.get_watchlisted_tasks(page=1, limit=10, user_id=user_id)
            
            self.assertIsInstance(result, GetWatchlistTasksResponse)
            self.assertEqual(len(result.tasks), 1)
            self.assertEqual(result.tasks[0].taskId, task_id)
            self.assertEqual(result.tasks[0].title, "Unassigned Task")
            
            # Verify assignee is None (task belongs to no one)
            self.assertIsNone(result.tasks[0].assignee)

    def test_add_task_validation_fails_invalid_task_id(self):
        """Test that validation fails with invalid task ID"""
        task_id = "invalid-id"
        user_id = str(ObjectId())
        created_by = str(ObjectId())

        dto = CreateWatchlistDTO(
            taskId=task_id, userId=user_id, createdBy=created_by, createdAt=datetime.now(timezone.utc)
        )

        error_response = ApiErrorResponse(statusCode=400, message=ApiErrors.INVALID_TASK_ID, errors=[])

        with patch("todo.services.watchlist_service.validate_task_exists", side_effect=ValueError(error_response)):
            with self.assertRaises(ValueError) as context:
                WatchlistService.add_task(dto)

            self.assertEqual(context.exception.args[0], error_response)

    def test_add_task_validation_fails_task_not_found(self):
        """Test that validation fails when task doesn't exist"""
        task_id = str(ObjectId())
        user_id = str(ObjectId())
        created_by = str(ObjectId())

        dto = CreateWatchlistDTO(
            taskId=task_id, userId=user_id, createdBy=created_by, createdAt=datetime.now(timezone.utc)
        )

        error_response = ApiErrorResponse(statusCode=404, message=ApiErrors.TASK_NOT_FOUND.format(task_id), errors=[])

        with patch("todo.services.watchlist_service.validate_task_exists", side_effect=ValueError(error_response)):
            with self.assertRaises(ValueError) as context:
                WatchlistService.add_task(dto)

            self.assertEqual(context.exception.args[0], error_response)

    def test_update_task_validation_fails_invalid_task_id(self):
        """Test that update validation fails with invalid task ID"""
        task_id = ObjectId()
        user_id = ObjectId()
        dto = {"isActive": True}

        error_response = ApiErrorResponse(statusCode=400, message=ApiErrors.INVALID_TASK_ID, errors=[])

        with patch("todo.services.watchlist_service.validate_task_exists", side_effect=ValueError(error_response)):
            with self.assertRaises(ValueError) as context:
                WatchlistService.update_task(task_id, dto, user_id)

            self.assertEqual(context.exception.args[0], error_response)
