from unittest import TestCase
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from todo.serializers.update_task_serializer import UpdateTaskSerializer
from todo.constants.task import TaskPriority, TaskStatus
from todo.constants.messages import ValidationErrors


class UpdateTaskSerializerTests(TestCase):
    def setUp(self):
        self.valid_object_id_str = str(ObjectId())
        self.future_date = datetime.now(timezone.utc) + timedelta(days=1)
        self.past_date = datetime.now(timezone.utc) - timedelta(days=1)

    def test_valid_full_payload(self):
        data = {
            "title": "Updated Test Task",
            "description": "This is an updated description.",
            "priority": TaskPriority.HIGH.name,
            "status": TaskStatus.IN_PROGRESS.name,
            "assignee": "user_assignee_id",
            "labels": [str(ObjectId()), str(ObjectId())],
            "dueAt": self.future_date.isoformat(),
            "startedAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "isAcknowledged": True,
        }
        serializer = UpdateTaskSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        validated_data = serializer.validated_data
        self.assertEqual(validated_data["title"], data["title"])
        self.assertEqual(validated_data["description"], data["description"])
        self.assertEqual(validated_data["priority"], data["priority"])
        self.assertEqual(validated_data["status"], data["status"])
        self.assertEqual(validated_data["assignee"], data["assignee"])
        self.assertEqual(validated_data["labels"], data["labels"])
        self.assertEqual(validated_data["dueAt"], datetime.fromisoformat(data["dueAt"]))
        self.assertEqual(validated_data["startedAt"], datetime.fromisoformat(data["startedAt"]))
        self.assertEqual(validated_data["isAcknowledged"], data["isAcknowledged"])

    def test_partial_payload_title_only(self):
        data = {"title": "Only Title Update"}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["title"], data["title"])
        self.assertEqual(len(serializer.validated_data), 1)

    def test_all_fields_can_be_null_or_empty_if_allowed(self):
        data = {
            "description": None,
            "priority": None,
            "status": None,
            "assignee": None,
            "labels": None,
            "dueAt": None,
            "startedAt": None,
        }
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertNotIn("title", serializer.validated_data)
        self.assertIsNone(serializer.validated_data.get("description"))
        self.assertIsNone(serializer.validated_data.get("priority"))
        self.assertIsNone(serializer.validated_data.get("status"))
        self.assertIsNone(serializer.validated_data.get("assignee"))
        self.assertIsNone(serializer.validated_data.get("labels"))
        self.assertIsNone(serializer.validated_data.get("dueAt"))
        self.assertIsNone(serializer.validated_data.get("startedAt"))

    def test_title_validation_blank(self):
        data = {"title": "   "}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)
        self.assertEqual(str(serializer.errors["title"][0]), ValidationErrors.BLANK_TITLE)

    def test_title_valid(self):
        data = {"title": "Valid Title"}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["title"], "Valid Title")

    def test_labels_validation_invalid_object_id(self):
        data = {"labels": [self.valid_object_id_str, "invalid-id"]}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("labels", serializer.errors)
        self.assertIn(ValidationErrors.INVALID_OBJECT_ID.format("invalid-id"), str(serializer.errors["labels"]))

    def test_labels_validation_valid_object_ids(self):
        valid_ids = [str(ObjectId()), str(ObjectId())]
        data = {"labels": valid_ids}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["labels"], valid_ids)

    def test_labels_can_be_empty_list(self):
        data = {"labels": []}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["labels"], [])

    def test_due_at_validation_past_date(self):
        data = {"dueAt": self.past_date.isoformat()}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("dueAt", serializer.errors)
        self.assertEqual(str(serializer.errors["dueAt"][0]), ValidationErrors.PAST_DUE_DATE)

    def test_due_at_validation_future_date(self):
        data = {"dueAt": self.future_date.isoformat()}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["dueAt"], datetime.fromisoformat(data["dueAt"]))

    def test_due_at_can_be_null(self):
        data = {"dueAt": None}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["dueAt"])

    def test_assignee_validation_blank_string_becomes_none(self):
        data = {"assignee": "   "}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["assignee"])

    def test_assignee_valid_string(self):
        data = {"assignee": "user123"}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["assignee"], "user123")

    def test_assignee_can_be_null(self):
        data = {"assignee": None}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["assignee"])

    def test_priority_invalid_choice(self):
        data = {"priority": "VERY_HIGH"}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("priority", serializer.errors)
        self.assertIn("is not a valid choice.", str(serializer.errors["priority"][0]))

    def test_status_invalid_choice(self):
        data = {"status": "PENDING_APPROVAL"}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)
        self.assertIn("is not a valid choice.", str(serializer.errors["status"][0]))

    def test_is_acknowledged_valid(self):
        data = {"isAcknowledged": True}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.validated_data["isAcknowledged"])

        data = {"isAcknowledged": False}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data["isAcknowledged"])

    def test_description_can_be_null(self):
        data = {"description": None}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get("description"))

    def test_description_can_be_empty_string(self):
        data = {"description": ""}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get("description"), "")

    def test_started_at_can_be_null(self):
        data = {"startedAt": None}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get("startedAt"))

    def test_started_at_valid_datetime(self):
        date_val = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        data = {"startedAt": date_val}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["startedAt"], datetime.fromisoformat(date_val))
