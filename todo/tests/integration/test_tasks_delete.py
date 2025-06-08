from bson import ObjectId
from http import HTTPStatus
from rest_framework.test import APIClient
from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import BaseMongoTestCase


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
        error_message = f"Task with ID {self.non_existent_id} not found."
        self.assertEqual(response_data["message"], error_message)
        error = response_data["errors"][0]
        self.assertEqual(error["source"]["path"], "task_id")
        self.assertEqual(error["title"], "Resource Not Found")
        self.assertEqual(error["detail"], error_message)

    def test_delete_task_invalid_id_format(self):
        response = self.client.delete(f"/v1/tasks/{self.invalid_task_id}")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["message"], "Please enter a valid Task ID format.")
        self.assertEqual(data["errors"][0]["source"]["path"], "task_id")
        self.assertEqual(data["errors"][0]["title"], "Validation Error")
        self.assertEqual(data["errors"][0]["detail"], "Please enter a valid Task ID format.")
