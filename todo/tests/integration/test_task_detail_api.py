from http import HTTPStatus
from django.urls import reverse
from bson import ObjectId
from datetime import datetime, timezone
from todo.tests.fixtures.task import tasks_db_data
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.constants.messages import ApiErrors, ValidationErrors


class TaskDetailAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.tasks.delete_many({})
        self.db.task_details.delete_many({})

        self.task_doc = tasks_db_data[1].copy()
        self.task_doc["_id"] = self.task_doc.pop("id")
        # Remove assignee from task document since it's now in separate collection
        self.task_doc.pop("assignee", None)
        self.task_doc["createdBy"] = str(self.user_id)
        self.task_doc["updatedBy"] = str(self.user_id)
        self.db.tasks.insert_one(self.task_doc)

        # Create assignee task details in separate collection
        assignee_details = {
            "_id": str(ObjectId()),
            "assignee_id": str(self.user_id),
            "task_id": str(self.task_doc["_id"]),
            "user_type": "user",
            "is_active": True,
            "created_by": str(self.user_id),
            "updated_by": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        }
        self.db.task_details.insert_one(assignee_details)

        self.existing_task_id = str(self.task_doc["_id"])
        self.non_existent_id = str(ObjectId())
        self.invalid_task_id = "invalid-task-id"

    def test_get_task_by_id_success(self):
        url = reverse("task_detail", args=[self.existing_task_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], self.existing_task_id)
        self.assertEqual(data["title"], self.task_doc["title"])
        self.assertEqual(data["priority"], "MEDIUM")
        self.assertEqual(data["status"], self.task_doc["status"])
        self.assertEqual(data["displayId"], self.task_doc["displayId"])
        self.assertEqual(data["createdBy"]["id"], self.task_doc["createdBy"])
        # Check that assignee details are included
        self.assertIsNotNone(data["assignee"])
        self.assertEqual(data["assignee"]["assignee_id"], str(self.user_id))
        self.assertEqual(data["assignee"]["user_type"], "user")

    def test_get_task_by_id_not_found(self):
        url = reverse("task_detail", args=[self.non_existent_id])
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
        url = reverse("task_detail", args=[self.invalid_task_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(data["errors"][0]["source"]["path"], "task_id")
        self.assertEqual(data["errors"][0]["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(data["errors"][0]["detail"], ValidationErrors.INVALID_TASK_ID_FORMAT)
