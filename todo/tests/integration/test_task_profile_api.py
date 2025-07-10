from http import HTTPStatus
from django.urls import reverse
from bson import ObjectId
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from datetime import datetime, timezone


class TaskProfileAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("tasks")
        self.db.tasks.delete_many({})

    def test_get_tasks_profile_true_requires_auth(self):
        client = self.client.__class__()
        response = client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_get_tasks_profile_true_returns_only_user_tasks(self):
        my_task = {
            "title": "My Task",
            "description": "Test desc",
            "createdBy": str(self.user_id),
            "assignee": str(self.user_id),
            "status": "TODO",
            "priority": 1,
            "labels": [],
            "isAcknowledged": False,
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": None,
            "dueAt": datetime.now(timezone.utc),
            "displayId": "#1",
        }
        other_task = {
            "title": "Other Task",
            "description": "Other desc",
            "createdBy": str(ObjectId()),
            "assignee": str(ObjectId()),
            "status": "TODO",
            "priority": 1,
            "labels": [],
            "isAcknowledged": False,
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": None,
            "dueAt": datetime.now(timezone.utc),
            "displayId": "#2",
        }
        self.db.tasks.insert_one(my_task)
        self.db.tasks.insert_one(other_task)
        response = self.client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertTrue(any(task["title"] == "My Task" for task in data["tasks"]))
        self.assertFalse(any(task["title"] == "Other Task" for task in data["tasks"]))

    def test_get_tasks_profile_true_empty_for_no_tasks(self):
        self.db.tasks.delete_many({})
        response = self.client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["tasks"], [])
