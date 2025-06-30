from http import HTTPStatus
from django.urls import reverse
from bson import ObjectId

from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import BaseMongoTestCase
from todo.constants.messages import ValidationErrors, ApiErrors
from todo.utils.google_jwt_utils import generate_google_token_pair

user_data = {
    "user_id": str(ObjectId()),
    "google_id": "test_google_id",
    "email": "test@example.com",
    "name": "Test User",
}


class AuthenticatedMongoTestCase(BaseMongoTestCase):
    def setUp(self):
        super().setUp()
        self._setup_auth_cookies()

    def _setup_auth_cookies(self):
        tokens = generate_google_token_pair(user_data)
        self.client.cookies["ext-access"] = tokens["access_token"]
        self.client.cookies["ext-refresh"] = tokens["refresh_token"]


class TaskDeleteAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.tasks.delete_many({})
        task_doc = tasks_db_data[0].copy()
        task_doc["_id"] = task_doc.pop("id")
        task_doc["assignee"] = user_data["user_id"]
        self.db.tasks.insert_one(task_doc)
        self.existing_task_id = str(task_doc["_id"])
        self.non_existent_id = str(ObjectId())
        self.invalid_task_id = "invalid-task-id"

    def test_delete_task_success(self):
        url = reverse("task_detail", args=[self.existing_task_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_delete_task_not_found(self):
        url = reverse("task_detail", args=[self.non_existent_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response_data = response.json()
        error_message = ApiErrors.TASK_NOT_FOUND.format(self.non_existent_id)
        self.assertEqual(response_data["message"], error_message)
        error = response_data["errors"][0]
        self.assertEqual(error["source"]["path"], "task_id")
        self.assertEqual(error["title"], ApiErrors.RESOURCE_NOT_FOUND_TITLE)
        self.assertEqual(error["detail"], error_message)

    def test_delete_task_invalid_id_format(self):
        url = reverse("task_detail", args=[self.invalid_task_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(data["errors"][0]["source"]["path"], "task_id")
        self.assertEqual(data["errors"][0]["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(data["errors"][0]["detail"], ValidationErrors.INVALID_TASK_ID_FORMAT)
