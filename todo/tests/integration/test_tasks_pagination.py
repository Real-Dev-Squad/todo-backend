from unittest import TestCase
from django.conf import settings
from rest_framework.test import APIRequestFactory

from todo.views.task import TaskView


class TaskPaginationIntegrationTest(TestCase):
    """Integration tests for task pagination settings"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskView.as_view()

    def test_pagination_settings_integration(self):
        """Test that the view and serializer correctly use Django settings for pagination"""
        # Test with no query params (should use default limit)
        request = self.factory.get("/tasks")
        response = self.view(request)
        
        # Check serializer validation passed and returned 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Verify API rejects values above max limit
        max_limit = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
        request = self.factory.get("/tasks", {"limit": str(max_limit + 1)})
        response = self.view(request)
        
        # Should get a 400 error
        self.assertEqual(response.status_code, 400)
        self.assertIn(str(max_limit), str(response.data)) 