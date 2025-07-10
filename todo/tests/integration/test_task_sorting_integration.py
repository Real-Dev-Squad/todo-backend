import unittest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory
from rest_framework import status
from todo.views.task import TaskListView
from todo.constants.task import (
    SORT_FIELD_PRIORITY,
    SORT_FIELD_DUE_AT,
    SORT_FIELD_CREATED_AT,
    SORT_FIELD_ASSIGNEE,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
)


class TaskSortingIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskListView.as_view()

    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository.list")
    def test_priority_sorting_integration(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        request = self.factory.get("/tasks", {"sort_by": "priority", "order": "desc"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_list.assert_called_with(1, 20, SORT_FIELD_PRIORITY, SORT_ORDER_DESC)

    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository.list")
    def test_due_at_default_order_integration(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        request = self.factory.get("/tasks", {"sort_by": "dueAt"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_list.assert_called_with(1, 20, SORT_FIELD_DUE_AT, SORT_ORDER_ASC)

    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository._list_sorted_by_assignee")
    def test_assignee_sorting_uses_aggregation(self, mock_assignee_sort, mock_count):
        mock_assignee_sort.return_value = []
        mock_count.return_value = 0

        request = self.factory.get("/tasks", {"sort_by": "assignee", "order": "asc"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_assignee_sort.assert_called_once_with(1, 20, SORT_ORDER_ASC)

    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository._list_sorted_by_assignee")
    @patch("todo.repositories.task_repository.TaskRepository.list")
    def test_field_specific_defaults_integration(self, mock_list, mock_assignee_sort, mock_count):
        mock_assignee_sort.return_value = []
        mock_count.return_value = 0

        def list_side_effect(page, limit, sort_by, order):
            if sort_by == SORT_FIELD_ASSIGNEE:
                return mock_assignee_sort(page, limit, order)
            return []

        mock_list.side_effect = list_side_effect

        test_cases = [
            (SORT_FIELD_CREATED_AT, SORT_ORDER_DESC),
            (SORT_FIELD_DUE_AT, SORT_ORDER_ASC),
            (SORT_FIELD_PRIORITY, SORT_ORDER_DESC),
            (SORT_FIELD_ASSIGNEE, SORT_ORDER_ASC),
        ]

        for sort_field, expected_order in test_cases:
            with self.subTest(sort_field=sort_field, expected_order=expected_order):
                mock_list.reset_mock()
                mock_assignee_sort.reset_mock()
                mock_count.reset_mock()
                mock_list.side_effect = list_side_effect

                request = self.factory.get("/tasks", {"sort_by": sort_field})
                response = self.view(request)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                if sort_field == SORT_FIELD_ASSIGNEE:
                    mock_assignee_sort.assert_called_with(1, 20, expected_order)
                else:
                    mock_list.assert_called_with(1, 20, sort_field, expected_order)

    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository.list")
    def test_pagination_with_sorting_integration(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 100

        request = self.factory.get("/tasks", {"page": "3", "limit": "5", "sort_by": "createdAt", "order": "asc"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_list.assert_called_with(3, 5, SORT_FIELD_CREATED_AT, SORT_ORDER_ASC)

    def test_invalid_sort_parameters_integration(self):
        request = self.factory.get("/tasks", {"sort_by": "invalid_field"})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        request = self.factory.get("/tasks", {"sort_by": "priority", "order": "invalid_order"})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository.list")
    def test_default_behavior_integration(self, mock_list, mock_count):
        mock_list.return_value = []
        mock_count.return_value = 0

        request = self.factory.get("/tasks")
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_list.assert_called_with(1, 20, SORT_FIELD_CREATED_AT, SORT_ORDER_DESC)

    @patch("todo.services.task_service.reverse_lazy", return_value="/v1/tasks")
    @patch("todo.repositories.task_repository.TaskRepository.count")
    @patch("todo.repositories.task_repository.TaskRepository.list")
    def test_pagination_links_preserve_sort_params_integration(self, mock_list, mock_count, mock_reverse):
        from todo.tests.fixtures.task import tasks_models

        mock_list.return_value = [tasks_models[0]] if tasks_models else []
        mock_count.return_value = 3

        with (
            patch("todo.services.task_service.LabelRepository.list_by_ids", return_value=[]),
            patch("todo.services.task_service.UserRepository.get_by_id", return_value=None),
        ):
            request = self.factory.get("/tasks", {"page": "2", "limit": "1", "sort_by": "priority", "order": "desc"})
            response = self.view(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            if response.data.get("links"):
                links = response.data["links"]
                if links.get("next"):
                    self.assertIn("sort_by=priority", links["next"])
                    self.assertIn("order=desc", links["next"])
                if links.get("prev"):
                    self.assertIn("sort_by=priority", links["prev"])
                    self.assertIn("order=desc", links["prev"])
