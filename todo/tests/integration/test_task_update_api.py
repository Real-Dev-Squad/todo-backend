from datetime import datetime, timedelta
from http import HTTPStatus

from bson import ObjectId
from django.urls import reverse
from todo.constants.messages import ApiErrors, ValidationErrors
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.tests.fixtures.task import tasks_db_data


class TaskUpdateAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.tasks.delete_many({})

        doc = tasks_db_data[0].copy()
        self.task_id = ObjectId()
        doc["_id"] = self.task_id
        doc.pop("id", None)
        doc["assignee"] = str(self.user_id)
        doc["createdBy"] = str(self.user_id)

        doc["createdAt"] = datetime.utcnow() - timedelta(days=1)
        self.db.tasks.insert_one(doc)

        self.valid_id = str(self.task_id)
        self.missing_id = str(ObjectId())
        self.bad_id = "bad-task-id"

    def test_update_task_success(self):
        url = reverse("task_detail", args=[self.valid_id])
        payload = {
            "title": "Updated Task Title",
            "description": "Updated via integration-test.",
            "priority": "LOW",
            "status": "IN_PROGRESS",
            "isAcknowledged": False,
        }
        res = self.client.patch(url, data=payload, format="json")
        self.assertEqual(res.status_code, HTTPStatus.OK)
        body = res.json()
        self.assertEqual(body["id"], self.valid_id)
        self.assertEqual(body["title"], payload["title"])
        self.assertEqual(body["description"], payload["description"])
        self.assertEqual(body["priority"], payload["priority"])
        self.assertEqual(body["status"], payload["status"])
        self.assertEqual(body["isAcknowledged"], payload["isAcknowledged"])
        updated_at = datetime.fromisoformat(body["updatedAt"].replace("Z", ""))
        self.assertTrue(datetime.utcnow() - updated_at < timedelta(minutes=1))

    def test_update_task_not_found(self):
        url = reverse("task_detail", args=[self.missing_id])
        res = self.client.patch(url, data={"title": "ghost"}, format="json")
        self.assertEqual(res.status_code, HTTPStatus.NOT_FOUND)
        msg = ApiErrors.TASK_NOT_FOUND.format(self.missing_id)
        self.assertEqual(res.json()["message"], msg)
        err = res.json()["errors"][0]
        self.assertEqual(err["title"], ApiErrors.RESOURCE_NOT_FOUND_TITLE)
        self.assertEqual(err["detail"], msg)
        self.assertEqual(err["source"]["path"], "task_id")

    def test_update_task_invalid_id_format(self):
        url = reverse("task_detail", args=[self.bad_id])
        res = self.client.patch(url, data={"title": "bad"}, format="json")
        self.assertEqual(res.status_code, HTTPStatus.BAD_REQUEST)
        body = res.json()
        self.assertEqual(body["statusCode"], HTTPStatus.BAD_REQUEST)
        self.assertEqual(body["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        err = body["errors"][0]
        self.assertEqual(err["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(err["detail"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(err["source"]["path"], "task_id")
