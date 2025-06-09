from http import HTTPStatus
from bson import ObjectId
from rest_framework.test import APIClient
from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import BaseMongoTestCase
from todo.constants.messages import ApiErrors, ValidationErrors

class TaskDetailAPIIntegrationTest(BaseMongoTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture_task = tasks_db_data[1].copy()
        cls.fixture_task["_id"] = cls.fixture_task.pop("id")
        cls.db.tasks.insert_one(cls.fixture_task)
        cls.existing_task_id = str(cls.fixture_task["_id"])
        cls.non_existent_id = str(ObjectId())
        cls.invalid_task_id = "invalid-task-id"
        cls.client = APIClient()

    def test_get_task_by_id_success(self):
        response = self.client.get(f"/v1/tasks/{self.existing_task_id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], self.existing_task_id)
        self.assertEqual(data["title"], self.fixture_task["title"])
        self.assertEqual(data["priority"], "MEDIUM")
        self.assertEqual(data["status"], self.fixture_task["status"])
        self.assertEqual(data["displayId"], self.fixture_task["displayId"])
        self.assertEqual(data["createdBy"]["id"], self.fixture_task["createdBy"])

    def test_get_task_by_id_not_found(self):
        response = self.client.get(f"/v1/tasks/{self.non_existent_id}")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        data = response.json()
        error_message = ApiErrors.TASK_NOT_FOUND.format(self.non_existent_id)
        self.assertEqual(data["message"], error_message)
        error = data["errors"][0]
        self.assertEqual(error["source"]["path"], "task_id")
        self.assertEqual(error["title"], ApiErrors.RESOURCE_NOT_FOUND_TITLE)
        self.assertEqual(error["detail"], error_message)

    def test_get_task_by_id_invalid_format(self):
        response = self.client.get(f"/v1/tasks/{self.invalid_task_id}")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(data["errors"][0]["source"]["path"], "task_id")
        self.assertEqual(data["errors"][0]["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(data["errors"][0]["detail"], ValidationErrors.INVALID_TASK_ID_FORMAT)
