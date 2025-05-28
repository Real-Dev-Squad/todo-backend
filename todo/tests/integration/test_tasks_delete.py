from unittest import TestCase
from unittest.mock import patch
from bson import ObjectId
from rest_framework.test import APIRequestFactory
from rest_framework import status

from todo.views.task import TaskDetailView
from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.constants.messages import ApiErrors


class DeleteTaskIntegrationTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskDetailView.as_view()
        self.valid_task_id = str(ObjectId())
        self.invalid_task_id = "invalid-task-id"

    @patch("todo.services.task_service.TaskService.delete_task")
    def test_delete_task_success(self, mock_delete_task):
        request = self.factory.delete(f"/tasks/{self.valid_task_id}")
        response = self.view(request, task_id=self.valid_task_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_delete_task.assert_called_once_with(self.valid_task_id)

    @patch("todo.services.task_service.TaskService.delete_task")
    def test_delete_task_not_found(self, mock_delete_task):
        mock_delete_task.side_effect = TaskNotFoundException(task_id=self.valid_task_id)

        request = self.factory.delete(f"/tasks/{self.valid_task_id}")
        response = self.view(request, task_id=self.valid_task_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Task Not Found")
        self.assertEqual(response.data["errors"][0]["source"]["parameter"], "task_id")

    def test_delete_task_invalid_id(self):
        request = self.factory.delete(f"/tasks/{self.invalid_task_id}")
        response = self.view(request, task_id=self.invalid_task_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], ApiErrors.TASK_NOT_FOUND)
        self.assertEqual(response.data["errors"][0]["source"]["parameter"], "task_id")
        self.assertEqual(response.data["errors"][0]["detail"], "Please enter a valid Task ID format.")
