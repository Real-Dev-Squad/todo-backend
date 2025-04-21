from rest_framework.reverse import reverse
from rest_framework.test import APISimpleTestCase, APIClient
from rest_framework import status
from unittest.mock import patch
from todo.constants.health import AppHealthStatus, ComponentHealthStatus


class HealthAPITests(APISimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    @patch(target="todo_project.db.config.DatabaseManager.check_database_health", return_value=True)
    def test_health_api_returns_200_when_db_healthy(self, mocked):
        url = reverse("health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AppHealthStatus.UP.name)
        self.assertEqual(response.data["components"]["db"]["status"], ComponentHealthStatus.UP.name)

    @patch(target="todo_project.db.config.DatabaseManager.check_database_health", return_value=False)
    def test_health_api_returns_503_when_db_not_healthy(self, mocked):
        url = reverse("health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["status"], AppHealthStatus.DOWN.name)
        self.assertEqual(response.data["components"]["db"]["status"], ComponentHealthStatus.DOWN.name)
