import unittest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory
from rest_framework import status
from todo.views.task import TaskListView
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.tests.fixtures.task import task_dtos
from todo.constants.task import (
    SORT_FIELD_PRIORITY,
    SORT_FIELD_DUE_AT,
    SORT_FIELD_CREATED_AT,
    SORT_FIELD_ASSIGNEE,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
)


class TaskViewSortingTests(unittest.TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskListView.as_view()

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_sort_by_priority(self, mock_get_tasks):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        request = self.factory.get("/tasks", {"sort_by": "priority"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_tasks.assert_called_once_with(page=1, limit=20, sort_by=SORT_FIELD_PRIORITY, order=None)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_sort_by_and_order(self, mock_get_tasks):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        request = self.factory.get("/tasks", {"sort_by": "dueAt", "order": "desc"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_tasks.assert_called_once_with(page=1, limit=20, sort_by=SORT_FIELD_DUE_AT, order=SORT_ORDER_DESC)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_all_sort_fields(self, mock_get_tasks):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        sort_fields = [SORT_FIELD_PRIORITY, SORT_FIELD_DUE_AT, SORT_FIELD_CREATED_AT, SORT_FIELD_ASSIGNEE]

        for sort_field in sort_fields:
            with self.subTest(sort_field=sort_field):
                mock_get_tasks.reset_mock()

                request = self.factory.get("/tasks", {"sort_by": sort_field})
                response = self.view(request)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                mock_get_tasks.assert_called_once_with(page=1, limit=20, sort_by=sort_field, order=None)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_all_order_values(self, mock_get_tasks):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        order_values = [SORT_ORDER_ASC, SORT_ORDER_DESC]

        for order in order_values:
            with self.subTest(order=order):
                mock_get_tasks.reset_mock()

                request = self.factory.get("/tasks", {"sort_by": SORT_FIELD_PRIORITY, "order": order})
                response = self.view(request)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                mock_get_tasks.assert_called_once_with(page=1, limit=20, sort_by=SORT_FIELD_PRIORITY, order=order)

    def test_get_tasks_with_invalid_sort_by(self):
        request = self.factory.get("/tasks", {"sort_by": "invalid_field"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_detail = str(response.data)
        self.assertIn("sort_by", error_detail)

    def test_get_tasks_with_invalid_order(self):
        request = self.factory.get("/tasks", {"sort_by": SORT_FIELD_PRIORITY, "order": "invalid_order"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_detail = str(response.data)
        self.assertIn("order", error_detail)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_sorting_with_pagination(self, mock_get_tasks):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        request = self.factory.get(
            "/tasks", {"page": "2", "limit": "15", "sort_by": SORT_FIELD_DUE_AT, "order": SORT_ORDER_ASC}
        )
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_tasks.assert_called_once_with(page=2, limit=15, sort_by=SORT_FIELD_DUE_AT, order=SORT_ORDER_ASC)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_default_behavior_unchanged(self, mock_get_tasks):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        request = self.factory.get("/tasks")
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_tasks.assert_called_once_with(page=1, limit=20, sort_by=SORT_FIELD_CREATED_AT, order=None)

    def test_get_tasks_edge_case_combinations(self):
        with patch("todo.services.task_service.TaskService.get_tasks") as mock_get_tasks:
            mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

            request = self.factory.get("/tasks", {"order": SORT_ORDER_ASC})
            response = self.view(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_get_tasks.assert_called_once_with(
                page=1, limit=20, sort_by=SORT_FIELD_CREATED_AT, order=SORT_ORDER_ASC
            )
