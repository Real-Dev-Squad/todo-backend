from unittest import TestCase

from todo.serializers.create_task_serializer import CreateTaskSerializer
from datetime import datetime, timedelta, timezone


class CreateTaskSerializerTest(TestCase):
    def setUp(self):
        self.valid_data = {
            "title": "Test task",
            "description": "Some test description",
            "priority": "LOW",
            "status": "TODO",
            "assignee": "dev001",
            "labels": [],
            "dueAt": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
        }

    def test_serializer_validates_correct_data(self):
        serializer = CreateTaskSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_fails_without_title(self):
        data = self.valid_data.copy()
        del data["title"]
        serializer = CreateTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_serializer_rejects_invalid_status(self):
        data = self.valid_data.copy()
        data["status"] = "INVALID"
        serializer = CreateTaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)
