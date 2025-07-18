from http import HTTPStatus
from django.urls import reverse
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase


class TaskProfileAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("tasks")
        self.db.tasks.delete_many({})
        # Remove manual user insertion; AuthenticatedMongoTestCase already creates the user

    def test_get_tasks_profile_true_requires_auth(self):
        client = self.client.__class__()
        response = client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_get_tasks_profile_true_empty_for_no_tasks(self):
        self.db.tasks.delete_many({})
        response = self.client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["tasks"], [])
