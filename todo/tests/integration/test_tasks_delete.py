from http import HTTPStatus
from bson import ObjectId
from rest_framework.test import APIClient
from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import BaseMongoTestCase
from todo.constants.messages import ValidationErrors, ApiErrors

class TaskDeleteAPIIntegrationTest(BaseMongoTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        task_doc = tasks_db_data[0].copy()
        task_doc["_id"] = task_doc.pop("id")
        cls.db.tasks.insert_one(task_doc)
        cls.existing_task_id = str(task_doc["_id"])
        cls.non_existent_id = str(ObjectId())
        cls.invalid_task_id = "invalid-task-id"
        cls.client = APIClient()

    def test_delete_task_success(self):
        response = self.client.delete(f"/v1/tasks/{self.existing_task_id}")
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_delete_task_not_found(self):
        response = self.client.delete(f"/v1/tasks/{self.non_existent_id}")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response_data = response.json()
        error_message = ApiErrors.TASK_NOT_FOUND.format(self.non_existent_id)
        self.assertEqual(response_data["message"], error_message)
        error = response_data["errors"][0]
        self.assertEqual(error["source"]["path"], "task_id")
        self.assertEqual(error["title"], ApiErrors.RESOURCE_NOT_FOUND_TITLE)
        self.assertEqual(error["detail"], error_message)

    def test_delete_task_invalid_id_format(self):
        response = self.client.delete(f"/v1/tasks/{self.invalid_task_id}")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(data["errors"][0]["source"]["path"], "task_id")
        self.assertEqual(data["errors"][0]["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(data["errors"][0]["detail"], ValidationErrors.INVALID_TASK_ID_FORMAT)
