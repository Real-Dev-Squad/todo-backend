from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from bson import ObjectId

from todo.services.task_service import TaskService
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorSource
from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.tests.fixtures.task import task_dtos
from todo.constants.task import TaskPriority, TaskStatus


class TaskDetailAPIIntegrationTest(APITestCase):
    @patch("todo.services.task_service.TaskService.get_task_by_id")
    def test_get_task_by_id_success(self, mock_get_task_by_id):
        fixture_task_dto = task_dtos[0]
        task_id_str = fixture_task_dto.id

        mock_get_task_by_id.return_value = fixture_task_dto

        url = reverse("task_detail", args=[task_id_str])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data_outer = response.data
        response_data_inner = response_data_outer.get("data")
        self.assertIsNotNone(response_data_inner)

        self.assertEqual(response_data_inner["id"], fixture_task_dto.id)
        self.assertEqual(response_data_inner["title"], fixture_task_dto.title)

        self.assertEqual(response_data_inner["priority"], TaskPriority(fixture_task_dto.priority).name)
        self.assertEqual(response_data_inner["status"], TaskStatus(fixture_task_dto.status).value)

        self.assertEqual(response_data_inner["displayId"], fixture_task_dto.displayId)

        if fixture_task_dto.createdBy:
            self.assertEqual(response_data_inner["createdBy"]["id"], fixture_task_dto.createdBy.id)
            self.assertEqual(response_data_inner["createdBy"]["name"], fixture_task_dto.createdBy.name)

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

    @patch.object(TaskService, "get_task_by_id", wraps=TaskService.get_task_by_id)
    def test_get_task_by_id_invalid_format(self, mock_actual_get_task_by_id):
        invalid_task_id = "invalid-id"
        url = reverse("task_detail", args=[invalid_task_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], ApiErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(len(response.data["errors"]), 1)
        error_detail_obj = response.data["errors"][0]
        self.assertEqual(error_detail_obj["detail"], ApiErrors.INVALID_TASK_ID_FORMAT)
        self.assertIn(ApiErrorSource.PATH.value, error_detail_obj["source"])
        self.assertEqual(error_detail_obj["source"][ApiErrorSource.PATH.value], "task_id")
        self.assertEqual(error_detail_obj["title"], ApiErrors.VALIDATION_ERROR)
        mock_actual_get_task_by_id.assert_called_once_with(invalid_task_id)
