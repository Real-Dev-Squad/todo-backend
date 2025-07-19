from http import HTTPStatus
from django.urls import reverse
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase


class UserProfileAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("users")

    def test_user_profile_true_requires_auth(self):
        client = self.client.__class__()
        response = client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_user_profile_true_returns_user_info(self):
        response = self.client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], str(self.user_id))
        self.assertEqual(data["email"], self.user_data["email"])
