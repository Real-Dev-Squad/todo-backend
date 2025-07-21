import uuid
from rest_framework import status
from bson import ObjectId
from datetime import datetime, timezone

from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.models.watchlist import WatchlistModel


class WatchlistCheckViewTests(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/v1/watchlist/tasks/check"
        self.task_id = str(uuid.uuid4())

    def test_check_task_not_in_watchlist(self):
        """Test that a task not in watchlist returns null."""
        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["in_watchlist"])

    def test_check_task_in_watchlist(self):
        """Test that a task in watchlist returns true."""
        # Create a watchlist entry
        watchlist_entry = WatchlistModel(
            taskId=self.task_id,
            userId=str(self.user_id),
            isActive=True,
            createdAt=datetime.now(timezone.utc),
            createdBy=str(self.user_id),
        )
        self.db.watchlist.insert_one(watchlist_entry.model_dump(by_alias=True))

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["in_watchlist"], True)

    def test_check_task_in_watchlist_but_inactive(self):
        """Test that an inactive watchlist entry returns false."""
        # Create an inactive watchlist entry
        watchlist_entry = WatchlistModel(
            taskId=self.task_id,
            userId=str(self.user_id),
            isActive=False,
            createdAt=datetime.now(timezone.utc),
            createdBy=str(self.user_id),
        )
        self.db.watchlist.insert_one(watchlist_entry.model_dump(by_alias=True))

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["in_watchlist"], False)

    def test_check_missing_task_id(self):
        """Test that missing task_id returns 400."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("task_id is required", response.data["message"])

    def test_check_invalid_task_id(self):
        """Test that invalid task_id returns 400."""
        response = self.client.get(f"{self.url}?task_id=invalid_id")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid task_id", response.data["message"])

    def test_check_task_in_watchlist_with_updated_by(self):
        """Test that a task with updatedBy ObjectId works correctly."""
        # Create a watchlist entry with updatedBy as ObjectId
        watchlist_doc = {
            "taskId": self.task_id,
            "userId": str(self.user_id),
            "isActive": True,
            "createdAt": datetime.now(timezone.utc),
            "createdBy": str(self.user_id),
            "updatedBy": ObjectId(),  # This should be converted to string
            "updatedAt": datetime.now(timezone.utc),
        }
        self.db.watchlist.insert_one(watchlist_doc)

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["in_watchlist"], True)
