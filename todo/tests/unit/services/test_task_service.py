from unittest.mock import Mock, patch, MagicMock
from unittest import TestCase
from django.core.paginator import Page, Paginator, EmptyPage
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, timezone
from bson import ObjectId

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
from todo.constants.messages import ApiErrors, ValidationErrors
from todo.repositories.task_repository import TaskRepository
from todo.models.label import LabelModel
from todo.models.common.pyobjectid import PyObjectId
from rest_framework.exceptions import ValidationError as DRFValidationError


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


class TaskServiceUpdateTests(TestCase):
    def setUp(self):
        self.task_id_str = str(ObjectId())
        self.user_id_str = "test_user_123"
        self.default_task_model = TaskModel(
            id=ObjectId(self.task_id_str),
            displayId="#TSK1",
            title="Original Task Title",
            description="Original Description",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.TODO,
            createdBy="system",
            createdAt=datetime.now(timezone.utc) - timedelta(days=2),
        )
        self.label_id_1_str = str(ObjectId())
        self.label_id_2_str = str(ObjectId())
        self.mock_label_1 = LabelModel(
            id=PyObjectId(self.label_id_1_str),
            name="Label One",
            color="#FF0000",
            createdBy="system",
            createdAt=datetime.now(timezone.utc),
        )
        self.mock_label_2 = LabelModel(
            id=PyObjectId(self.label_id_2_str),
            name="Label Two",
            color="#00FF00",
            createdBy="system",
            createdAt=datetime.now(timezone.utc),
        )

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_update_task_success_full_payload(
        self, mock_prepare_dto, mock_list_labels, mock_repo_update, mock_repo_get_by_id
    ):
        mock_repo_get_by_id.return_value = self.default_task_model

        updated_task_model_from_repo = self.default_task_model.model_copy(deep=True)
        updated_task_model_from_repo.title = "Updated Title via Service"
        updated_task_model_from_repo.status = TaskStatus.IN_PROGRESS
        updated_task_model_from_repo.priority = TaskPriority.HIGH
        updated_task_model_from_repo.description = "New Description"
        updated_task_model_from_repo.assignee = "new_assignee_id"
        updated_task_model_from_repo.dueAt = datetime.now(timezone.utc) + timedelta(days=5)
        updated_task_model_from_repo.startedAt = datetime.now(timezone.utc) - timedelta(hours=2)
        updated_task_model_from_repo.isAcknowledged = True
        updated_task_model_from_repo.labels = [PyObjectId(self.label_id_1_str)]
        updated_task_model_from_repo.updatedBy = self.user_id_str
        updated_task_model_from_repo.updatedAt = datetime.now(timezone.utc)
        mock_repo_update.return_value = updated_task_model_from_repo

        mock_dto_response = MagicMock(spec=TaskDTO)
        mock_prepare_dto.return_value = mock_dto_response

        mock_list_labels.return_value = [self.mock_label_1]

        validated_data_from_serializer = {
            "title": "Updated Title via Service",
            "description": "New Description",
            "priority": TaskPriority.HIGH.name,
            "status": TaskStatus.IN_PROGRESS.name,
            "assignee": "new_assignee_id",
            "labels": [self.label_id_1_str],
            "dueAt": datetime.now(timezone.utc) + timedelta(days=5),
            "startedAt": datetime.now(timezone.utc) - timedelta(hours=2),
            "isAcknowledged": True,
        }

        result_dto = TaskService.update_task(self.task_id_str, validated_data_from_serializer, self.user_id_str)

        mock_repo_get_by_id.assert_called_once_with(self.task_id_str)
        mock_list_labels.assert_called_once_with([PyObjectId(self.label_id_1_str)])

        mock_repo_update.assert_called_once()
        call_args = mock_repo_update.call_args[0]
        self.assertEqual(call_args[0], self.task_id_str)
        update_payload_sent_to_repo = call_args[1]

        self.assertEqual(update_payload_sent_to_repo["title"], validated_data_from_serializer["title"])
        self.assertEqual(update_payload_sent_to_repo["status"], TaskStatus.IN_PROGRESS.value)
        self.assertEqual(update_payload_sent_to_repo["priority"], TaskPriority.HIGH.value)
        self.assertEqual(update_payload_sent_to_repo["description"], validated_data_from_serializer["description"])
        self.assertEqual(update_payload_sent_to_repo["assignee"], validated_data_from_serializer["assignee"])
        self.assertEqual(update_payload_sent_to_repo["dueAt"], validated_data_from_serializer["dueAt"])
        self.assertEqual(update_payload_sent_to_repo["startedAt"], validated_data_from_serializer["startedAt"])
        self.assertEqual(
            update_payload_sent_to_repo["isAcknowledged"], validated_data_from_serializer["isAcknowledged"]
        )
        self.assertEqual(update_payload_sent_to_repo["labels"], [PyObjectId(self.label_id_1_str)])
        self.assertEqual(update_payload_sent_to_repo["updatedBy"], self.user_id_str)

        mock_prepare_dto.assert_called_once_with(updated_task_model_from_repo)
        self.assertEqual(result_dto, mock_dto_response)

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_update_task_no_actual_changes_returns_current_task_dto(
        self, mock_prepare_dto, mock_repo_update, mock_repo_get_by_id
    ):
        mock_repo_get_by_id.return_value = self.default_task_model
        mock_dto_response = MagicMock(spec=TaskDTO)
        mock_prepare_dto.return_value = mock_dto_response

        validated_data_empty = {}
        result_dto = TaskService.update_task(self.task_id_str, validated_data_empty, self.user_id_str)

        mock_repo_get_by_id.assert_called_once_with(self.task_id_str)
        mock_repo_update.assert_not_called()
        mock_prepare_dto.assert_called_once_with(self.default_task_model)
        self.assertEqual(result_dto, mock_dto_response)

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    def test_update_task_raises_task_not_found(self, mock_repo_get_by_id):
        mock_repo_get_by_id.return_value = None
        validated_data = {"title": "some update"}

        with self.assertRaises(TaskNotFoundException) as context:
            TaskService.update_task(self.task_id_str, validated_data, self.user_id_str)

        self.assertEqual(str(context.exception), ApiErrors.TASK_NOT_FOUND.format(self.task_id_str))
        mock_repo_get_by_id.assert_called_once_with(self.task_id_str)

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    def test_update_task_raises_drf_validation_error_for_missing_labels(self, mock_list_labels, mock_repo_get_by_id):
        mock_repo_get_by_id.return_value = self.default_task_model
        mock_list_labels.return_value = [self.mock_label_1]

        label_id_non_existent = str(ObjectId())
        validated_data_with_bad_label = {"labels": [self.label_id_1_str, label_id_non_existent]}

        with self.assertRaises(DRFValidationError) as context:
            TaskService.update_task(self.task_id_str, validated_data_with_bad_label, self.user_id_str)

        self.assertIn("labels", context.exception.detail)
        self.assertIn(
            ValidationErrors.MISSING_LABEL_IDS.format(label_id_non_existent), context.exception.detail["labels"]
        )
        mock_repo_get_by_id.assert_called_once_with(self.task_id_str)
        mock_list_labels.assert_called_once_with([PyObjectId(self.label_id_1_str), PyObjectId(label_id_non_existent)])

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    def test_update_task_raises_task_not_found_if_repo_update_fails(self, mock_repo_update, mock_repo_get_by_id):
        mock_repo_get_by_id.return_value = self.default_task_model
        mock_repo_update.return_value = None

        validated_data = {"title": "Updated Title"}

        with self.assertRaises(TaskNotFoundException) as context:
            TaskService.update_task(self.task_id_str, validated_data, self.user_id_str)

        self.assertEqual(str(context.exception), ApiErrors.TASK_NOT_FOUND.format(self.task_id_str))
        mock_repo_get_by_id.assert_called_once_with(self.task_id_str)
        mock_repo_update.assert_called_once_with(self.task_id_str, {**validated_data, "updatedBy": self.user_id_str})

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_update_task_clears_labels_when_labels_is_none(
        self, mock_prepare_dto, mock_repo_update, mock_repo_get_by_id
    ):
        mock_repo_get_by_id.return_value = self.default_task_model
        updated_task_model_from_repo = self.default_task_model.model_copy(deep=True)
        updated_task_model_from_repo.labels = []
        mock_repo_update.return_value = updated_task_model_from_repo
        mock_prepare_dto.return_value = MagicMock(spec=TaskDTO)

        validated_data = {"labels": None}
        TaskService.update_task(self.task_id_str, validated_data, self.user_id_str)

        _, kwargs_update = mock_repo_update.call_args
        update_payload = mock_repo_update.call_args[0][1]
        self.assertEqual(update_payload["labels"], [])

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_update_task_sets_empty_labels_list_when_labels_is_empty_list(
        self, mock_prepare_dto, mock_list_labels, mock_repo_update, mock_repo_get_by_id
    ):
        mock_repo_get_by_id.return_value = self.default_task_model
        updated_task_model_from_repo = self.default_task_model.model_copy(deep=True)
        updated_task_model_from_repo.labels = []
        mock_repo_update.return_value = updated_task_model_from_repo
        mock_prepare_dto.return_value = MagicMock(spec=TaskDTO)
        mock_list_labels.return_value = []

        validated_data = {"labels": []}
        TaskService.update_task(self.task_id_str, validated_data, self.user_id_str)

        update_payload_sent_to_repo = mock_repo_update.call_args[0][1]
        self.assertEqual(update_payload_sent_to_repo["labels"], [])
        mock_list_labels.assert_not_called()

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_update_task_converts_priority_and_status_names_to_values(
        self, mock_prepare_dto, mock_repo_update, mock_repo_get_by_id
    ):
        mock_repo_get_by_id.return_value = self.default_task_model
        updated_task_model_from_repo = self.default_task_model.model_copy(deep=True)
        mock_repo_update.return_value = updated_task_model_from_repo
        mock_prepare_dto.return_value = MagicMock(spec=TaskDTO)

        validated_data = {"priority": TaskPriority.LOW.name, "status": TaskStatus.DONE.name}
        TaskService.update_task(self.task_id_str, validated_data, self.user_id_str)

        update_payload_sent_to_repo = mock_repo_update.call_args[0][1]
        self.assertEqual(update_payload_sent_to_repo["priority"], TaskPriority.LOW.value)
        self.assertEqual(update_payload_sent_to_repo["status"], TaskStatus.DONE.value)

    @patch("todo.services.task_service.TaskRepository.get_by_id")
    @patch("todo.services.task_service.TaskRepository.update")
    @patch("todo.services.task_service.TaskService.prepare_task_dto")
    def test_update_task_handles_null_priority_and_status(
        self, mock_prepare_dto, mock_repo_update, mock_repo_get_by_id
    ):
        mock_repo_get_by_id.return_value = self.default_task_model
        updated_task_model_from_repo = self.default_task_model.model_copy(deep=True)
        mock_repo_update.return_value = updated_task_model_from_repo
        mock_prepare_dto.return_value = MagicMock(spec=TaskDTO)

        validated_data = {"priority": None, "status": None}
        TaskService.update_task(self.task_id_str, validated_data, self.user_id_str)

        update_payload_sent_to_repo = mock_repo_update.call_args[0][1]
        self.assertIsNone(update_payload_sent_to_repo["priority"])
        self.assertIsNone(update_payload_sent_to_repo["status"])
