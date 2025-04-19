# todo/tests/integration/views/test_task_creation.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from datetime import datetime, timedelta, timezone


class CreateTaskIntegrationTests(APITestCase):
    def setUp(self):
        self.url = reverse("tasks")
        self.valid_payload = {
            "title": "Integration Test Title",
            "description": "Description for Integration tests",
            "priority": "HIGH",
            "status": "TODO",
            "assignee": "user123",
            "labels": [],
            "dueAt": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
        }

    def test_create_task_successfully(self):
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["title"], self.valid_payload["title"])

    def test_create_task_fails_with_blank_title(self):
        payload = self.valid_payload.copy()
        payload["title"] = " "
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["source"]["parameter"] == "title" for err in response.data["errors"]))

    def test_create_task_fails_with_invalid_priority(self):
        payload = self.valid_payload.copy()
        payload["priority"] = "INVALID"
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["source"]["parameter"] == "priority" for err in response.data["errors"]))

    def test_create_task_fails_with_due_date_in_past(self):
        payload = self.valid_payload.copy()
        payload["dueAt"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(err["source"]["parameter"] == "dueAt" for err in response.data["errors"]))

    def test_create_task_treats_blank_assignee_as_null(self):
        payload = self.valid_payload.copy()
        payload["assignee"] = ""
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["data"].get("assignee"))
