from unittest import TestCase
from rest_framework.test import APISimpleTestCase, APIClient, APIRequestFactory
from rest_framework.reverse import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from rest_framework.response import Response
from django.conf import settings

from todo.views.task import TaskView
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.tests.fixtures.task import task_dtos


class TaskViewTests(APISimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("tasks")
        self.valid_params = {"page": 1, "limit": 10}

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_returns_200_for_valid_params(self, mock_get_tasks: Mock):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        response: Response = self.client.get(self.url, self.valid_params)

        mock_get_tasks.assert_called_once_with(1, 10)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = mock_get_tasks.return_value.model_dump(mode="json", exclude_none=True)
        self.assertDictEqual(response.data, expected_response)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_returns_200_without_params(self, mock_get_tasks: Mock):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        response: Response = self.client.get(self.url)
        default_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
        mock_get_tasks.assert_called_once_with(1, default_limit)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_tasks_returns_400_for_invalid_query_params(self):
        invalid_params = {
            "page": "invalid",
            "limit": -1,
        }

        response: Response = self.client.get(self.url, invalid_params)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        expected_response = {
            "statusCode": 400,
            "message": "Invalid request",
            "errors": [
                {"source": {"parameter": "page"}, "detail": "A valid integer is required."},
                {"source": {"parameter": "limit"}, "detail": "limit must be greater than or equal to 1"},
            ],
        }
        response_data = response.data

        self.assertEqual(response_data["statusCode"], expected_response["statusCode"])
        self.assertEqual(response_data["message"], expected_response["message"], "Error message mismatch")

        for actual_error, expected_error in zip(response_data["errors"], expected_response["errors"]):
            self.assertEqual(actual_error["source"]["parameter"], expected_error["source"]["parameter"])
            self.assertEqual(actual_error["detail"], expected_error["detail"])


class TaskViewUnitTest(TestCase):
    """Unit tests using APIRequestFactory for direct view testing"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskView.as_view()

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_default_pagination(self, mock_get_tasks):
        """Test GET /tasks without any query parameters uses default pagination"""
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)
        
        request = self.factory.get("/tasks")
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        default_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
        mock_get_tasks.assert_called_once_with(1, default_limit)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_valid_pagination(self, mock_get_tasks):
        """Test GET /tasks with valid page and limit parameters"""
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)
        
        request = self.factory.get("/tasks", {"page": "2", "limit": "15"})
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_tasks.assert_called_once_with(2, 15)

    def test_get_tasks_with_invalid_page(self):
        """Test GET /tasks with invalid page parameter"""
        request = self.factory.get("/tasks", {"page": "0"})
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_detail = str(response.data)
        self.assertIn("page", error_detail)
        self.assertIn("greater than or equal to 1", error_detail)

    def test_get_tasks_with_invalid_limit(self):
        """Test GET /tasks with invalid limit parameter"""
        request = self.factory.get("/tasks", {"limit": "0"})
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_detail = str(response.data)
        self.assertIn("limit", error_detail)
        self.assertIn("greater than or equal to 1", error_detail)

    def test_get_tasks_with_non_numeric_parameters(self):
        """Test GET /tasks with non-numeric parameters"""
        request = self.factory.get("/tasks", {"page": "abc", "limit": "def"})
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_detail = str(response.data)
        self.assertTrue("page" in error_detail or "limit" in error_detail)
