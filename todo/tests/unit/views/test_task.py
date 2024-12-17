from rest_framework.test import APISimpleTestCase, APIClient
from rest_framework.reverse import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from rest_framework.response import Response
from todo.constants.task import DEFAULT_PAGE_LIMIT
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
        mock_get_tasks.assert_called_once_with(1, DEFAULT_PAGE_LIMIT)
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
