import unittest
from unittest.mock import patch, MagicMock
from todo.services.task_service import TaskService
from todo.constants.task import (
    SORT_FIELD_PRIORITY,
    SORT_FIELD_DUE_AT,
    SORT_FIELD_CREATED_AT,
    SORT_FIELD_ASSIGNEE,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
)


class TaskServiceSortingTests(unittest.TestCase):
    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_default_sorting(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        TaskService.get_tasks()

        mock_list.assert_called_once_with(1, 20, SORT_FIELD_CREATED_AT, SORT_ORDER_DESC)

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_explicit_sort_by_priority(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        TaskService.get_tasks(sort_by=SORT_FIELD_PRIORITY, order=SORT_ORDER_DESC)

        mock_list.assert_called_once_with(1, 20, SORT_FIELD_PRIORITY, SORT_ORDER_DESC)

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_sort_by_due_at_default_order(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        TaskService.get_tasks(sort_by=SORT_FIELD_DUE_AT, order=None)

        mock_list.assert_called_once_with(1, 20, SORT_FIELD_DUE_AT, SORT_ORDER_ASC)

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_sort_by_priority_default_order(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        TaskService.get_tasks(sort_by=SORT_FIELD_PRIORITY, order=None)

        mock_list.assert_called_once_with(1, 20, SORT_FIELD_PRIORITY, SORT_ORDER_DESC)

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_sort_by_assignee_default_order(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        TaskService.get_tasks(sort_by=SORT_FIELD_ASSIGNEE, order=None)

        mock_list.assert_called_once_with(1, 20, SORT_FIELD_ASSIGNEE, SORT_ORDER_ASC)

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_sort_by_created_at_default_order(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        TaskService.get_tasks(sort_by=SORT_FIELD_CREATED_AT, order=None)

        mock_list.assert_called_once_with(1, 20, SORT_FIELD_CREATED_AT, SORT_ORDER_DESC)

    @patch("todo.services.task_service.reverse_lazy", return_value="/v1/tasks")
    def test_build_page_url_includes_sort_parameters(self, mock_reverse):
        url = TaskService.build_page_url(2, 10, SORT_FIELD_PRIORITY, SORT_ORDER_DESC)

        expected_url = "/v1/tasks?page=2&limit=10&sort_by=priority&order=desc"
        self.assertEqual(url, expected_url)

    @patch("todo.services.task_service.reverse_lazy", return_value="/v1/tasks")
    def test_build_page_url_with_default_sort_parameters(self, mock_reverse):
        url = TaskService.build_page_url(1, 20, SORT_FIELD_DUE_AT, None)

        expected_url = "/v1/tasks?page=1&limit=20&sort_by=dueAt&order=asc"
        self.assertEqual(url, expected_url)

    @patch("todo.services.task_service.TaskRepository.count")
    @patch("todo.services.task_service.TaskRepository.list")
    def test_get_tasks_pagination_links_preserve_sort_params(self, mock_list, mock_count):
        """Test that pagination links preserve sort parameters"""
        from todo.tests.fixtures.task import tasks_models

        mock_user = MagicMock()
        mock_user.name = "Test User"

        mock_list.return_value = [tasks_models[0]]
        mock_count.return_value = 3

        with (
            patch("todo.services.task_service.LabelRepository.list_by_ids", return_value=[]),
            patch("todo.services.task_service.UserRepository.get_by_id", return_value=mock_user),
            patch("todo.services.task_service.reverse_lazy", return_value="/v1/tasks"),
        ):
            response = TaskService.get_tasks(page=2, limit=1, sort_by=SORT_FIELD_PRIORITY, order=SORT_ORDER_DESC)

            self.assertIsNotNone(response.links)
            self.assertIn("sort_by=priority", response.links.next)
            self.assertIn("order=desc", response.links.next)
            self.assertIn("sort_by=priority", response.links.prev)
            self.assertIn("order=desc", response.links.prev)
