from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from bson import ObjectId
from unittest.mock import patch
from datetime import datetime

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.constants.task import TaskPriority, TaskStatus
from todo.dto.user_dto import UserDTO
from todo.dto.task_dto import TaskDTO


class TaskDetailAPIIntegrationTest(APITestCase):
    def setUp(self):
        pass

    @patch("todo.services.task_service.TaskService.get_task_by_id")
    def test_get_task_by_id_success(self, mock_get_task_by_id):
        task_id_str = str(ObjectId())
        created_by_user_id = str(ObjectId())

        task_dto_data = {
            "id": task_id_str,
            "displayId": "#123",
            "title": "Mocked Task Title",
            "description": "Mocked task description",
            "priority": TaskPriority.MEDIUM,
            "status": TaskStatus.IN_PROGRESS,
            "assignee": None,
            "createdBy": UserDTO(id=created_by_user_id, name="Creator User"),
            "labels": [],
            "startedAt": None,
            "dueAt": datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
            "createdAt": datetime.fromisoformat("2024-01-01T09:00:00+00:00"),
            "updatedAt": None,
            "isAcknowledged": False,
        }

        mock_service_return_value = TaskDTO(**task_dto_data)
        mock_get_task_by_id.return_value = mock_service_return_value

        url = reverse("task_detail", args=[task_id_str])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data_outer = response.data

        response_data_inner = response_data_outer.get("data")
        self.assertIsNotNone(response_data_inner)
        self.assertEqual(response_data_inner["id"], task_id_str)
        self.assertEqual(response_data_inner["title"], task_dto_data["title"])

        self.assertEqual(response_data_inner["priority"], TaskPriority.MEDIUM.name)
        self.assertEqual(response_data_inner["status"], TaskStatus.IN_PROGRESS.value)
        self.assertEqual(response_data_inner["displayId"], task_dto_data["displayId"])
        self.assertEqual(response_data_inner["createdBy"]["id"], created_by_user_id)
        self.assertEqual(response_data_inner["createdBy"]["name"], "Creator User")

        mock_get_task_by_id.assert_called_once_with(task_id_str)

    @patch("todo.services.task_service.TaskService.get_task_by_id")
    def test_get_task_by_id_not_found(self, mock_get_task_by_id):
        non_existent_id = str(ObjectId())
        mock_get_task_by_id.side_effect = TaskNotFoundException("Task not found")

        url = reverse("task_detail", args=[non_existent_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = response.data.get("errors", [{}])[0].get("detail")
        self.assertEqual(error_detail, "Task not found")
        mock_get_task_by_id.assert_called_once_with(non_existent_id)

    @patch("todo.services.task_service.TaskService.get_task_by_id")
    def test_get_task_by_id_invalid_format(self, mock_get_task_by_id):
        invalid_id = "this-is-not-an-object-id"
        mock_get_task_by_id.side_effect = ValueError("Invalid ObjectId format")

        url = reverse("task_detail", args=[invalid_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_detail = response.data.get("errors", [{}])[0].get("detail")
        self.assertEqual(error_detail, "Invalid ObjectId format")

        mock_get_task_by_id.assert_called_once_with(invalid_id)
