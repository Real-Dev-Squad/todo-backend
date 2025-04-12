from unittest import TestCase
from rest_framework.test import APISimpleTestCase, APIClient, APIRequestFactory
from rest_framework.reverse import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from rest_framework.response import Response
from datetime import datetime, timedelta, timezone
from django.conf import settings

from todo.views.task import TaskView
from todo.dto.user_dto import UserDTO
from todo.dto.task_dto import TaskDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.tests.fixtures.task import task_dtos
from todo.constants.task import TaskPriority, TaskStatus


class TaskViewTests(APISimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("tasks")
        self.valid_params = {"page": 1, "limit": 10}

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_returns_200_for_valid_params(self, mock_get_tasks: Mock):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        response: Response = self.client.get(self.url, self.valid_params)

        mock_get_tasks.assert_called_once_with(page=1, limit=10)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = mock_get_tasks.return_value.model_dump(mode="json", exclude_none=True)
        self.assertDictEqual(response.data, expected_response)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_returns_200_without_params(self, mock_get_tasks: Mock):
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        response: Response = self.client.get(self.url)
        default_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
        mock_get_tasks.assert_called_once_with(page=1, limit=default_limit)
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


class TaskViewTest(TestCase):
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
        mock_get_tasks.assert_called_once_with(page=1, limit=default_limit)

    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_get_tasks_with_valid_pagination(self, mock_get_tasks):
        """Test GET /tasks with valid page and limit parameters"""
        mock_get_tasks.return_value = GetTasksResponse(tasks=task_dtos)

        request = self.factory.get("/tasks", {"page": "2", "limit": "15"})
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_tasks.assert_called_once_with(page=2, limit=15)

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

class CreateTaskViewTests(APISimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("tasks")

        self.valid_payload = {
            "title": "Write tests",
            "description": "Cover all core paths",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "assignee": "developer1",
            "labels": [],
            "dueAt": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
        }

    @patch("todo.services.task_service.TaskService.create_task")
    def test_create_task_returns_201_on_success(self, mock_create_task):
        task_dto = TaskDTO(
            id="abc123",
            displayId="#1",
            title=self.valid_payload["title"],
            description=self.valid_payload["description"],
            priority=TaskPriority[self.valid_payload["priority"]],
            status=TaskStatus[self.valid_payload["status"]],
            assignee=UserDTO(id="developer1", name="SYSTEM"),
            isAcknowledged=False,
            labels=[],
            startedAt=datetime.now(timezone.utc),
            dueAt=datetime.fromisoformat(self.valid_payload["dueAt"].replace("Z", "+00:00")),
            createdAt=datetime.now(timezone.utc),
            updatedAt=None,
            createdBy=UserDTO(id="system", name="SYSTEM"),
            updatedBy=None
        )

        mock_create_task.return_value = CreateTaskResponse(data=task_dto)

        response: Response = self.client.post(self.url, data=self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["title"], self.valid_payload["title"])
        mock_create_task.assert_called_once()

    def test_create_task_returns_400_when_title_is_missing(self):
        invalid_payload = self.valid_payload.copy()
        del invalid_payload["title"]

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"], "validation_failed")
        self.assertEqual(response.data["statusCode"], 400)
        self.assertTrue(any(err["field"] == "title" for err in response.data["errors"]))

    def test_create_task_returns_400_when_title_blank(self):
        invalid_payload = self.valid_payload.copy()
        invalid_payload["title"] = " "

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["field"] == "title" for err in response.data["errors"]))

    def test_create_task_returns_400_for_invalid_priority(self):
        invalid_payload = self.valid_payload.copy()
        invalid_payload["priority"] = "SUPER"

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["field"] == "priority" for err in response.data["errors"]))

    def test_create_task_returns_400_for_invalid_status(self):
        invalid_payload = self.valid_payload.copy()
        invalid_payload["status"] = "WORKING"

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["field"] == "status" for err in response.data["errors"]))

    def test_create_task_returns_400_when_label_ids_are_not_objectids(self):
        invalid_payload = self.valid_payload.copy()
        invalid_payload["labels"] = ["invalid_id"]

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["field"] == "labels" for err in response.data["errors"]))

    def test_create_task_returns_400_when_dueAt_is_past(self):
        invalid_payload = self.valid_payload.copy()
        invalid_payload["dueAt"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["field"] == "dueAt" for err in response.data["errors"]))

    
    @patch("todo.services.task_service.TaskService.create_task")
    def test_create_task_handles_blank_assignee_as_null(self, mock_create_task):
        blank_assignee_payload = self.valid_payload.copy()
        blank_assignee_payload["assignee"] = ""

        task_dto = TaskDTO(
            id="abc123",
            displayId="#2",
            title=blank_assignee_payload["title"],
            description=blank_assignee_payload["description"],
            priority=TaskPriority[blank_assignee_payload["priority"]],
            status=TaskStatus[blank_assignee_payload["status"]],
            assignee=None,
            isAcknowledged=False,
            labels=[],
            startedAt=None,
            dueAt=datetime.fromisoformat(blank_assignee_payload["dueAt"].replace("Z", "+00:00")),
            createdAt=datetime.now(timezone.utc),
            updatedAt=None,
            createdBy=UserDTO(id="system", name="SYSTEM"),
            updatedBy=None
        )

        mock_create_task.return_value = CreateTaskResponse(data=task_dto)

        response = self.client.post(self.url, data=blank_assignee_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["data"].get("assignee"))

    @patch("todo.services.task_service.TaskService.create_task")
    def test_create_task_returns_500_on_internal_error(self, mock_create_task):
        mock_create_task.side_effect = Exception("Database exploded")

        response = self.client.post(self.url, data=self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["status"], "internal_server_error")
        self.assertEqual(response.data["statusCode"], 500)
        self.assertIn("An unexpected error occurred", response.data["errorMessage"])




