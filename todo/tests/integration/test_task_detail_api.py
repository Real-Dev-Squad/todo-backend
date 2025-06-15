from http import HTTPStatus
from bson import ObjectId
from django.urls import reverse
from rest_framework.test import APIClient
from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import BaseMongoTestCase
from todo.constants.messages import ApiErrors, ValidationErrors


class TaskDetailAPIIntegrationTest(BaseMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.tasks.delete_many({})  # Clear tasks to avoid DuplicateKeyError
        self.task_doc = tasks_db_data[1].copy()
        self.task_doc["_id"] = self.task_doc.pop("id")
        self.db.tasks.insert_one(self.task_doc)
        self.existing_task_id = str(self.task_doc["_id"])
        self.non_existent_id = str(ObjectId())
        self.invalid_task_id = "invalid-task-id"
        self.client = APIClient()

    def test_get_task_by_id_success(self):
        url = reverse('task_detail', args=[self.existing_task_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], self.existing_task_id)
        self.assertEqual(data["title"], self.task_doc["title"])
        self.assertEqual(data["priority"], "MEDIUM")
        self.assertEqual(data["status"], self.task_doc["status"])
        self.assertEqual(data["displayId"], self.task_doc["displayId"])
        self.assertEqual(data["createdBy"]["id"],
                         self.task_doc["createdBy"])

    def test_get_task_by_id_not_found(self):
        url = reverse('task_detail', args=[self.non_existent_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        data = response.json()
        error_message = ApiErrors.TASK_NOT_FOUND.format(self.non_existent_id)
        self.assertEqual(data["message"], error_message)
        error = data["errors"][0]
        self.assertEqual(error["source"]["path"], "task_id")
        self.assertEqual(error["title"], ApiErrors.RESOURCE_NOT_FOUND_TITLE)
        self.assertEqual(error["detail"], error_message)

    def test_get_task_by_id_invalid_format(self):
        url = reverse('task_detail', args=[self.invalid_task_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(
            data["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(data["errors"][0]["source"]["path"], "task_id")
        self.assertEqual(data["errors"][0]["title"],
                         ApiErrors.VALIDATION_ERROR)
        self.assertEqual(data["errors"][0]["detail"],
                         ValidationErrors.INVALID_TASK_ID_FORMAT)
