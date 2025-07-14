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
            "assignee": {"assignee_id": str(ObjectId()), "relation_type": "user"},
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
        data = {"assignee": None}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["assignee"])

    def test_assignee_valid_string(self):
        data = {"assignee": {"assignee_id": str(ObjectId()), "relation_type": "user"}}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["assignee"], data["assignee"])

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

    def test_started_at_validation_future_date(self):
        future_started_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        data = {"startedAt": future_started_at}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("startedAt", serializer.errors)
        self.assertEqual(str(serializer.errors["startedAt"][0]), ValidationErrors.FUTURE_STARTED_AT)

    def test_labels_validation_not_list_or_tuple(self):
        data = {"labels": "not-a-list-or-tuple"}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("labels", serializer.errors)
        self.assertEqual(str(serializer.errors["labels"][0]), 'Expected a list of items but got type "str".')

    def test_labels_validation_multiple_invalid_object_ids(self):
        invalid_id_1 = "invalid-id-1"
        invalid_id_2 = "invalid-id-2"
        data = {"labels": [self.valid_object_id_str, invalid_id_1, invalid_id_2]}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("labels", serializer.errors)

        label_errors = serializer.errors["labels"]
        self.assertIsInstance(label_errors, list)

        self.assertEqual(len(label_errors), 2)
        self.assertIn(ValidationErrors.INVALID_OBJECT_ID.format(invalid_id_1), label_errors)
        self.assertIn(ValidationErrors.INVALID_OBJECT_ID.format(invalid_id_2), label_errors)

    def test_labels_validation_mixed_valid_and_multiple_invalid_ids(self):
        valid_id_1 = str(ObjectId())
        invalid_id_1 = "bad-id-format-1"
        valid_id_2 = str(ObjectId())
        invalid_id_2 = "another-invalid"

        data = {"labels": [valid_id_1, invalid_id_1, valid_id_2, invalid_id_2]}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("labels", serializer.errors)

        label_errors = serializer.errors["labels"]
        self.assertIsInstance(label_errors, list)
        self.assertEqual(len(label_errors), 2)

        expected_error_messages = [
            ValidationErrors.INVALID_OBJECT_ID.format(invalid_id_1),
            ValidationErrors.INVALID_OBJECT_ID.format(invalid_id_2),
        ]

        for msg in expected_error_messages:
            self.assertIn(msg, label_errors)

    def test_rejects_invalid_assignee(self):
        data = {"assignee": {"assignee_id": "324324"}}
        serializer = UpdateTaskSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("assignee", serializer.errors)
