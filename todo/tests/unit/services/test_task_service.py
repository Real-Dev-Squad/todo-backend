from unittest.mock import Mock, patch, MagicMock
from unittest import TestCase
from django.core.paginator import Page, Paginator, EmptyPage
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, timezone

from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.paginated_response import LinksData
from todo.dto.user_dto import UserDTO
from todo.services.task_service import TaskService, PaginationConfig
from todo.dto.task_dto import TaskDTO
from todo.dto.task_dto import CreateTaskDTO
from todo.tests.fixtures.task import tasks_models
from todo.tests.fixtures.label import label_models
from todo.constants.task import TaskPriority, TaskStatus
from todo.models.task import TaskModel
from todo.exceptions.task_exceptions import TaskNotFoundException
from bson.errors import InvalidId as BsonInvalidId
from todo.constants.messages import ApiErrors
from todo.repositories.task_repository import TaskRepository


class TaskServiceTests(TestCase):
    @patch("todo.services.task_service.reverse_lazy", return_value="/v1/tasks")
    def setUp(self, mock_reverse_lazy):
        self.mock_reverse_lazy = mock_reverse_lazy

    @patch("todo.services.task_service.Paginator")
    @patch("todo.services.task_service.TaskRepository.get_all")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    def test_get_tasks_returns_paginated_response(
        self, mock_label_repo: Mock, mock_get_all: Mock, mock_paginator: Mock
    ):
        mock_get_all.return_value = tasks_models
        mock_label_repo.return_value = label_models

        mock_page = MagicMock(spec=Page)
        mock_page.object_list = [tasks_models[0]]
        mock_page.has_previous.return_value = True
        mock_page.has_next.return_value = True
        mock_page.previous_page_number.return_value = 1
        mock_page.next_page_number.return_value = 3

        mock_paginator_instance = MagicMock(spec=Paginator)
        mock_paginator_instance.page.return_value = mock_page
        mock_paginator.return_value = mock_paginator_instance

        response: GetTasksResponse = TaskService.get_tasks(page=2, limit=1)

        self.assertIsInstance(response, GetTasksResponse)
        self.assertEqual(len(response.tasks), 1)

        self.assertIsInstance(response.links, LinksData)
        self.assertEqual(response.links.next, f"{self.mock_reverse_lazy('tasks')}?page=3&limit=1")
        self.assertEqual(response.links.prev, f"{self.mock_reverse_lazy('tasks')}?page=1&limit=1")

        mock_get_all.assert_called_once()
        mock_paginator.assert_called_once_with(tasks_models, 1)
        mock_paginator_instance.page.assert_called_once_with(2)

    @patch("todo.services.task_service.Paginator")
    @patch("todo.services.task_service.TaskRepository.get_all")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    def test_get_tasks_doesnt_returns_prev_link_for_first_page(
        self, mock_label_repo: Mock, mock_get_all: Mock, mock_paginator: Mock
    ):
        mock_get_all.return_value = tasks_models
        mock_label_repo.return_value = label_models

        mock_page = MagicMock(spec=Page)
        mock_page.object_list = [tasks_models[0]]
        mock_page.has_previous.return_value = False
        mock_page.has_next.return_value = True
        mock_page.next_page_number.return_value = 2

        mock_paginator_instance = MagicMock(spec=Paginator)
        mock_paginator_instance.page.return_value = mock_page
        mock_paginator.return_value = mock_paginator_instance

        response: GetTasksResponse = TaskService.get_tasks(page=1, limit=1)

        self.assertIsNone(response.links.prev)

        self.assertEqual(response.links.next, f"{self.mock_reverse_lazy('tasks')}?page=2&limit=1")

    @patch("todo.services.task_service.TaskRepository.get_all")
    def test_get_tasks_returns_empty_response_if_no_tasks_present(self, mock_get_all: Mock):
        mock_get_all.return_value = []

        response: GetTasksResponse = TaskService.get_tasks(page=1, limit=10)

        self.assertIsInstance(response, GetTasksResponse)
        self.assertEqual(len(response.tasks), 0)
        self.assertIsNone(response.links)

        mock_get_all.assert_called_once()

    @patch("todo.services.task_service.Paginator")
    @patch("todo.services.task_service.TaskRepository.get_all")
    def test_get_tasks_returns_empty_response_when_page_exceeds_range(self, mock_get_all: Mock, mock_paginator: Mock):
        mock_get_all.return_value = tasks_models

        mock_paginator_instance = MagicMock(spec=Paginator)
        mock_paginator_instance.page.side_effect = EmptyPage("Empty page")
        mock_paginator.return_value = mock_paginator_instance

        response: GetTasksResponse = TaskService.get_tasks(page=999, limit=10)

        self.assertIsInstance(response, GetTasksResponse)
        self.assertEqual(len(response.tasks), 0)
        self.assertIsNone(response.links)

    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    def test_prepare_task_dto_maps_model_to_dto(self, mock_label_repo: Mock):
        task_model = tasks_models[0]
        mock_label_repo.return_value = label_models

        result: TaskDTO = TaskService.prepare_task_dto(task_model)

        mock_label_repo.assert_called_once_with(task_model.labels)

        self.assertIsInstance(result, TaskDTO)
        self.assertEqual(result.id, str(task_model.id))

    def test_prepare_user_dto_maps_model_to_dto(self):
        user_id = tasks_models[0].assignee
        result: UserDTO = TaskService.prepare_user_dto(user_id)

        self.assertIsInstance(result, UserDTO)
        self.assertEqual(result.id, user_id)
        self.assertEqual(result.name, "SYSTEM")

    def test_validate_pagination_params_with_valid_params(self):
        TaskService._validate_pagination_params(1, 10)

    def test_validate_pagination_params_with_invalid_page(self):
        with self.assertRaises(ValidationError) as context:
            TaskService._validate_pagination_params(0, 10)
        self.assertIn("Page must be a positive integer", str(context.exception))

    def test_validate_pagination_params_with_invalid_limit(self):
        with self.assertRaises(ValidationError) as context:
            TaskService._validate_pagination_params(1, 0)
        self.assertIn("Limit must be a positive integer", str(context.exception))

        with self.assertRaises(ValidationError) as context:
            TaskService._validate_pagination_params(1, PaginationConfig.MAX_LIMIT + 1)
        self.assertIn(f"Maximum limit of {PaginationConfig.MAX_LIMIT}", str(context.exception))

    def test_prepare_label_dtos_converts_ids_to_dtos(self):
        label_ids = ["label_id_1", "label_id_2"]

        with patch("todo.services.task_service.LabelRepository.list_by_ids") as mock_list_by_ids:
            mock_list_by_ids.return_value = label_models

            result = TaskService._prepare_label_dtos(label_ids)

            self.assertEqual(len(result), len(label_models))
            self.assertEqual(result[0].name, label_models[0].name)
            self.assertEqual(result[0].color, label_models[0].color)

            mock_list_by_ids.assert_called_once_with(label_ids)

    @patch("todo.services.task_service.Paginator")
    @patch("todo.services.task_service.TaskRepository.get_all")
    def test_get_tasks_handles_validation_error(self, mock_get_all: Mock, mock_paginator: Mock):
        mock_get_all.return_value = tasks_models

        with patch("todo.services.task_service.TaskService._validate_pagination_params") as mock_validate:
            mock_validate.side_effect = ValidationError("Test validation error")

            response = TaskService.get_tasks(page=1, limit=10)

            self.assertIsInstance(response, GetTasksResponse)
            self.assertEqual(len(response.tasks), 0)
            self.assertIsNone(response.links)

    @patch("todo.services.task_service.Paginator")
    @patch("todo.services.task_service.TaskRepository.get_all")
    def test_get_tasks_handles_general_exception(self, mock_get_all: Mock, mock_paginator: Mock):
        mock_get_all.side_effect = Exception("Test general error")

        response = TaskService.get_tasks(page=1, limit=10)

        self.assertIsInstance(response, GetTasksResponse)
        self.assertEqual(len(response.tasks), 0)
        self.assertIsNone(response.links)

    @patch("todo.services.task_service.TaskRepository.create")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_create_task_successfully_creates_task(self, mock_prepare_dto, mock_create):
        dto = CreateTaskDTO(
            title="Test Task",
            description="This is a test",
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO,
            assignee="user123",
            labels=[],
            dueAt=datetime.now(timezone.utc) + timedelta(days=1),
        )

        mock_task_model = MagicMock(spec=TaskModel)
        mock_create.return_value = mock_task_model
        mock_task_dto = MagicMock(spec=TaskDTO)
        mock_prepare_dto.return_value = mock_task_dto

        result = TaskService.create_task(dto)

        mock_create.assert_called_once()
        mock_prepare_dto.assert_called_once_with(mock_task_model)
        self.assertEqual(result.data, mock_task_dto)

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_get_task_by_id_success(self, mock_prepare_task_dto: Mock, mock_repo_get_by_id: Mock):
        task_id = "validtaskid123"
        mock_task_model = MagicMock(spec=TaskModel)
        mock_repo_get_by_id.return_value = mock_task_model

        mock_dto = MagicMock(spec=TaskDTO)
        mock_prepare_task_dto.return_value = mock_dto

        result_dto = TaskService.get_task_by_id(task_id)

        mock_repo_get_by_id.assert_called_once_with(task_id)
        mock_prepare_task_dto.assert_called_once_with(mock_task_model)
        self.assertEqual(result_dto, mock_dto)

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    def test_get_task_by_id_raises_task_not_found(self, mock_repo_get_by_id: Mock):
        mock_repo_get_by_id.return_value = None
        task_id = "6833661c84e8da308f27e0d55"
        expected_message = ApiErrors.TASK_NOT_FOUND.format(task_id)

        with self.assertRaises(TaskNotFoundException) as context:
            TaskService.get_task_by_id(task_id)

        self.assertEqual(str(context.exception), expected_message)
        mock_repo_get_by_id.assert_called_once_with(task_id)

    @patch.object(TaskRepository, "get_by_id", side_effect=BsonInvalidId("Invalid ObjectId"))
    def test_get_task_by_id_invalid_id_format(self, mock_get_by_id_repo_method: Mock):
        invalid_id = "invalid_id_format"

        with self.assertRaises(BsonInvalidId) as context:
            TaskService.get_task_by_id(invalid_id)

        self.assertEqual(str(context.exception), "Invalid ObjectId")
        mock_get_by_id_repo_method.assert_called_once_with(invalid_id)
