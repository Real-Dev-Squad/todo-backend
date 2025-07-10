from unittest import TestCase
from unittest.mock import patch
from django.conf import settings
from rest_framework.test import APIRequestFactory

from todo.views.task import TaskListView
from todo.dto.responses.get_tasks_response import GetTasksResponse


class TaskPaginationIntegrationTest(TestCase):
    """Integration tests for task pagination settings"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskListView.as_view()

    @patch("todo.middlewares.jwt_auth.JWTAuthenticationMiddleware._is_public_path")
    @patch("todo.services.task_service.TaskService.get_tasks")
    def test_pagination_settings_integration(self, mock_get_tasks, mock_is_public_path):
        """Test that the view and serializer correctly use Django settings for pagination"""
        mock_is_public_path.return_value = True
        mock_get_tasks.return_value = GetTasksResponse(tasks=[], links=None)

        default_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]

        request = self.factory.get("/tasks")
        request.user = None
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        mock_get_tasks.assert_called_with(page=1, limit=default_limit, sort_by="createdAt", order="desc")

        mock_get_tasks.reset_mock()

        request = self.factory.get("/tasks", {"limit": "10"})
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        mock_get_tasks.assert_called_with(page=1, limit=10, sort_by="createdAt", order="desc")

        # Verify API rejects values above max limit
        max_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
        request = self.factory.get("/tasks", {"limit": str(max_limit + 1)})
        response = self.view(request)

        # Should get a 400 error
        self.assertEqual(response.status_code, 400)
        self.assertIn(str(max_limit), str(response.data))
