from unittest.mock import Mock, patch
from unittest import TestCase

from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.paginated_response import LinksData
from todo.dto.user_dto import UserDTO
from todo.services.task_service import TaskService
from todo.dto.task_dto import TaskDTO
from todo.tests.fixtures.task import tasks_models
from todo.tests.fixtures.label import label_models


class TaskServiceTests(TestCase):
    @patch("todo.services.task_service.reverse_lazy", return_value="/v1/tasks")
    def setUp(self, mock_reverse_lazy):
        self.mock_reverse_lazy = mock_reverse_lazy

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    def test_get_tasks_returns_paginated_response(
        self, mock_label_repo: Mock, mock_task_repo: Mock, mock_task_count: Mock
    ):
        mock_task_repo.return_value = [tasks_models[0]]
        mock_label_repo.return_value = label_models
        mock_task_count.return_value = 5

        response: GetTasksResponse = TaskService.get_tasks(2, 1)
        self.assertIsInstance(response, GetTasksResponse)
        self.assertEqual(len(response.tasks), 1)

        self.assertIsInstance(response.links, LinksData)
        self.assertEqual(response.links.next, f"{self.mock_reverse_lazy('tasks')}?page=3&limit=1")
        self.assertEqual(response.links.prev, f"{self.mock_reverse_lazy('tasks')}?page=1&limit=1")

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    @patch("todo.services.task_service.LabelRepository.list_by_ids")
    def test_get_tasks_doesnt_returns_prev_link_for_first_page(
        self, mock_label_repo: Mock, mock_task_repo: Mock, mock_task_count: Mock
    ):
        mock_task_repo.return_value = [tasks_models[0]]
        mock_label_repo.return_value = label_models
        mock_task_count.return_value = 10

        response: GetTasksResponse = TaskService.get_tasks(1, 1)

        self.assertIsNone(response.links.prev)

    @patch("todo.services.task_service.TaskRepository.count")
    def test_get_tasks_returns_zero_tasks_if_no_tasks_present(self, mock_task_count: Mock):
        mock_task_count.return_value = 5

        response: GetTasksResponse = TaskService.get_tasks(2, 10)
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
