from django.test import TransactionTestCase
from bson import ObjectId
from http import HTTPStatus
from django.test import override_settings
from rest_framework.test import APIClient
from pymongo import MongoClient
from todo.tests.testcontainers.mongo_container import MongoReplicaSetContainer
from todo_project.db.config import DatabaseManager
from todo.tests.fixtures.task import tasks_db_data


@override_settings(DB_NAME="testdb")
class TaskDeleteAPIIntegrationTest(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mongo_container = MongoReplicaSetContainer()
        cls.mongo_container.start()
        cls.mongo_url = cls.mongo_container.get_connection_url()
        cls.mongo_client = MongoClient(cls.mongo_url)
        cls.db = cls.mongo_client.get_database("testdb")

        cls.override = override_settings(
            MONGODB_URI=cls.mongo_url,
            DB_NAME="testdb",
        )
        cls.override.enable()
        DatabaseManager().reset()
        task_doc = tasks_db_data[0].copy()
        task_doc["_id"] = task_doc.pop("id")
        cls.db.tasks.insert_one(task_doc)
        cls.existing_task_id = str(task_doc["_id"])
        cls.non_existent_id = str(ObjectId())
        cls.invalid_task_id = "invalid-task-id"
        cls.client = APIClient()

    @classmethod
    def tearDownClass(cls):
        cls.mongo_client.close()
        cls.mongo_container.stop()
        cls.override.disable()
        super().tearDownClass()

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
        response_data = response.json()
        self.assertEqual(response_data["message"], "Please enter a valid Task ID format.")
        self.assertEqual(response_data["errors"][0]["title"], "Validation Error")
