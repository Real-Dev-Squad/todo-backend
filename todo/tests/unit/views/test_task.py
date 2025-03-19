from unittest import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from rest_framework.exceptions import ValidationError

from todo.views.task import TaskView


class TaskViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = TaskView.as_view()

    def test_get_tasks_with_default_pagination(self):
        """Test GET /tasks without any query parameters uses default pagination"""
        request = self.factory.get("/tasks")
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify response uses default pagination
        self.assertEqual(response.data, {})

    def test_get_tasks_with_valid_pagination(self):
        """Test GET /tasks with valid page and limit parameters"""
        request = self.factory.get("/tasks", {"page": "2", "limit": "15"})
        response = self.view(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})

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