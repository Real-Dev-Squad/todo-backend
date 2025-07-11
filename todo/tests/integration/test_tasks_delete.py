from http import HTTPStatus
from django.urls import reverse
from bson import ObjectId
from datetime import datetime, timezone

from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.constants.messages import ValidationErrors, ApiErrors


class TaskDeleteAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.tasks.delete_many({})
        self.db.assignee_task_details.delete_many({})
        
        task_doc = tasks_db_data[0].copy()
        task_doc["_id"] = task_doc.pop("id")
        # Remove assignee from task document since it's now in separate collection
        task_doc.pop("assignee", None)
        self.db.tasks.insert_one(task_doc)
        
        # Create assignee task details in separate collection
        assignee_details = {
            "_id": ObjectId(),
            "assignee_id": ObjectId(self.user_data["user_id"]),
            "task_id": task_doc["_id"],
            "relation_type": "user",
            "is_action_taken": False,
            "is_active": True,
            "created_by": ObjectId(self.user_data["user_id"]),
            "updated_by": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        }
        self.db.assignee_task_details.insert_one(assignee_details)
        
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
