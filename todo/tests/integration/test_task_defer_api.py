from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from bson import ObjectId
from django.urls import reverse
from todo.constants.messages import ApiErrors, ValidationErrors
from todo.constants.task import MINIMUM_DEFERRAL_NOTICE_DAYS, TaskPriority, TaskStatus
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.tests.fixtures.task import tasks_db_data


class TaskDeferAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.tasks.delete_many({})
        self.db.task_details.delete_many({})

    def _insert_task(self, *, status: str = TaskStatus.TODO.value, due_at: datetime | None = None) -> str:
        task_fixture = tasks_db_data[0].copy()
        new_id = ObjectId()
        task_fixture["_id"] = new_id
        task_fixture.pop("id", None)
        task_fixture["displayId"] = "#IT-DEF"
        task_fixture["status"] = status
        # Remove assignee from task document since it's now in separate collection
        task_fixture.pop("assignee", None)
        task_fixture["createdBy"] = str(self.user_id)
        task_fixture["priority"] = TaskPriority.MEDIUM.value
        task_fixture["createdAt"] = datetime.now(timezone.utc)
        if due_at:
            task_fixture["dueAt"] = due_at
        else:
            task_fixture.pop("dueAt", None)

        self.db.tasks.insert_one(task_fixture)

        # Create assignee task details in separate collection
        assignee_details = {
            "_id": ObjectId(),
            "assignee_id": ObjectId(self.user_id),
            "task_id": new_id,
            "user_type": "user",
            "is_action_taken": False,
            "is_active": True,
            "created_by": ObjectId(self.user_id),
            "updated_by": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        }
        self.db.task_details.insert_one(assignee_details)

        return str(new_id)

    def test_defer_task_success(self):
        now = datetime.now(timezone.utc)
        due_at = now + timedelta(days=MINIMUM_DEFERRAL_NOTICE_DAYS + 30)
        task_id = self._insert_task(due_at=due_at)
        deferred_till = now + timedelta(days=10)

        url = reverse("task_detail", args=[task_id]) + "?action=defer"
        response = self.client.patch(url, data={"deferredTill": deferred_till.isoformat()}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = response.json()
        self.assertIn("deferredDetails", response_data)
        self.assertIsNotNone(response_data["deferredDetails"])
        raw_dt_str = response_data["deferredDetails"]["deferredTill"]

        if raw_dt_str.endswith("Z"):
            raw_dt_str = raw_dt_str.replace("Z", "+00:00")

        response_deferred_till = datetime.fromisoformat(raw_dt_str)

        if response_deferred_till.tzinfo is None:
            response_deferred_till = response_deferred_till.replace(tzinfo=timezone.utc)

        self.assertTrue(abs(response_deferred_till - deferred_till) < timedelta(seconds=1))

    def test_defer_task_too_close_to_due_date_returns_422(self):
        now = datetime.now(timezone.utc)
        due_at = now + timedelta(days=MINIMUM_DEFERRAL_NOTICE_DAYS + 5)
        task_id = self._insert_task(due_at=due_at)

        defer_limit = due_at - timedelta(days=MINIMUM_DEFERRAL_NOTICE_DAYS)
        deferred_till = defer_limit + timedelta(days=1)

        url = reverse("task_detail", args=[task_id]) + "?action=defer"
        response = self.client.patch(url, data={"deferredTill": deferred_till.isoformat()}, format="json")

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        response_json = response.json()
        self.assertEqual(response_json["statusCode"], HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(response_json["message"], ValidationErrors.CANNOT_DEFER_TOO_CLOSE_TO_DUE_DATE)
        error = response_json["errors"][0]
        self.assertEqual(error["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(error["detail"], ValidationErrors.CANNOT_DEFER_TOO_CLOSE_TO_DUE_DATE)
        self.assertEqual(error["source"]["parameter"], "deferredTill")

    def test_defer_done_task_returns_409(self):
        task_id = self._insert_task(status=TaskStatus.DONE.value)
        deferred_till = datetime.now(timezone.utc) + timedelta(days=5)

        url = reverse("task_detail", args=[task_id]) + "?action=defer"
        response = self.client.patch(url, data={"deferredTill": deferred_till.isoformat()}, format="json")

        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        response_data = response.json()
        self.assertEqual(response_data["statusCode"], HTTPStatus.CONFLICT)
        self.assertEqual(response_data["message"], ValidationErrors.CANNOT_DEFER_A_DONE_TASK)
        error = response_data["errors"][0]
        self.assertEqual(error["title"], ApiErrors.STATE_CONFLICT_TITLE)
        self.assertEqual(error["detail"], ValidationErrors.CANNOT_DEFER_A_DONE_TASK)
        self.assertEqual(error["source"]["path"], "task_id")

    def test_defer_task_with_invalid_date_format_returns_400(self):
        task_id = self._insert_task()
        url = reverse("task_detail", args=[task_id]) + "?action=defer"
        response = self.client.patch(url, data={"deferredTill": "invalid-date-format"}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = response.json()
        self.assertEqual(response_data["errors"][0]["source"]["parameter"], "deferredTill")

    def test_defer_task_with_missing_date_returns_400(self):
        task_id = self._insert_task()
        url = reverse("task_detail", args=[task_id]) + "?action=defer"
        response = self.client.patch(url, data={}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = response.json()
        self.assertEqual(response_data["errors"][0]["source"]["parameter"], "deferredTill")
        self.assertIn("required", response_data["errors"][0]["detail"])

    def test_defer_task_unauthorized(self):
        now = datetime.now(timezone.utc)
        due_at = now + timedelta(days=MINIMUM_DEFERRAL_NOTICE_DAYS + 30)
        task_id = self._insert_task(due_at=due_at)
        deferred_till = now + timedelta(days=10)
        url = reverse("task_detail", args=[task_id]) + "?action=defer"
        other_user_id = ObjectId()
        self._create_test_user(other_user_id)
        self._set_auth_cookies()

        response = self.client.patch(url, data={"deferredTill": deferred_till.isoformat()}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        response_data = response.json()
        self.assertEqual(response_data["message"], ApiErrors.UNAUTHORIZED_TITLE)
        err = response_data["errors"][0]
        self.assertEqual(err["title"], ApiErrors.UNAUTHORIZED_TITLE)
