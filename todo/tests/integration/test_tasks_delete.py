from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from bson import ObjectId
from unittest.mock import patch

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.tests.fixtures.task import task_dtos

class TaskDeleteAPIIntegrationTest(APITestCase):
    def setUp(self):
        self.task_id = task_dtos[0].id

    @patch("todo.repositories.task_repository.TaskRepository.delete_by_id")
    def test_delete_task_success(self, mock_delete_by_id):
        url = reverse("task_detail", args=[self.task_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("todo.repositories.task_repository.TaskRepository.delete_by_id")
    def test_delete_task_not_found(self, mock_delete_by_id):
        mock_delete_by_id.side_effect = TaskNotFoundException()
        non_existent_id = str(ObjectId())
        url = reverse("task_detail", args=[non_existent_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = response.data.get("errors", [{}])[0].get("detail")
        self.assertEqual(error_detail, "Task not found.")

    def test_delete_task_invalid_id_format(self):
        invalid_task_id = "invalid-id"
        url = reverse("task_detail", args=[invalid_task_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Please enter a valid Task ID format.")
        self.assertIsNotNone(response.data.get("errors"))
        self.assertEqual(len(response.data["errors"]), 1)

        error_obj = response.data["errors"][0]
        self.assertEqual(error_obj["detail"], "Please enter a valid Task ID format.")
        self.assertEqual(error_obj["source"]["path"], "task_id")
        self.assertEqual(error_obj["title"], "Validation Error")
