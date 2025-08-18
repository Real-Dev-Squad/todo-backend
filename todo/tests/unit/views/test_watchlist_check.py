from rest_framework import status
from rest_framework.test import APITestCase
from bson import ObjectId
from unittest.mock import patch, Mock
from django.conf import settings

from todo.models.watchlist import WatchlistModel
from todo.utils.jwt_utils import generate_token_pair


class WatchlistCheckViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.url = "/v1/watchlist/tasks/check"
        self.task_id = str(ObjectId())
        self.user_id = str(ObjectId())

        # Set up authentication
        self.user_data = {
            "user_id": self.user_id,
            "google_id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        tokens = generate_token_pair(self.user_data)
        self.client.cookies[settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME")] = tokens["access_token"]
        self.client.cookies[settings.COOKIE_SETTINGS.get("REFRESH_COOKIE_NAME")] = tokens["refresh_token"]

    @patch("todo.repositories.watchlist_repository.WatchlistRepository.get_by_user_and_task")
    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    def test_check_task_not_in_watchlist(self, mock_user_repo, mock_watchlist_repo):
        """Test that a task not in watchlist returns null."""
        from todo.models.user import UserModel

        mock_user = Mock(spec=UserModel)
        mock_user.email_id = "test@example.com"
        mock_user_repo.return_value = mock_user
        mock_watchlist_repo.return_value = None  # No watchlist entry

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["in_watchlist"])

    @patch("todo.repositories.watchlist_repository.WatchlistRepository.get_by_user_and_task")
    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    def test_check_task_in_watchlist(self, mock_user_repo, mock_watchlist_repo):
        """Test that a task in watchlist returns true."""
        from todo.models.user import UserModel

        mock_user = Mock(spec=UserModel)
        mock_user.email_id = "test@example.com"
        mock_user_repo.return_value = mock_user

        mock_watchlist_entry = Mock(spec=WatchlistModel)
        mock_watchlist_entry.isActive = True
        mock_watchlist_repo.return_value = mock_watchlist_entry

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["in_watchlist"], True)

    @patch("todo.repositories.watchlist_repository.WatchlistRepository.get_by_user_and_task")
    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    def test_check_task_in_watchlist_but_inactive(self, mock_user_repo, mock_watchlist_repo):
        """Test that an inactive watchlist entry returns false."""
        from todo.models.user import UserModel

        mock_user = Mock(spec=UserModel)
        mock_user.email_id = "test@example.com"
        mock_user_repo.return_value = mock_user

        mock_watchlist_entry = Mock(spec=WatchlistModel)
        mock_watchlist_entry.isActive = False
        mock_watchlist_repo.return_value = mock_watchlist_entry

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["in_watchlist"], False)

    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    def test_check_missing_task_id(self, mock_user_repo):
        """Test that missing task_id returns 400."""
        from todo.models.user import UserModel

        mock_user = Mock(spec=UserModel)
        mock_user.email_id = "test@example.com"
        mock_user_repo.return_value = mock_user

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("task_id is required", response.data["message"])

    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    def test_check_invalid_task_id(self, mock_user_repo):
        """Test that invalid task_id returns 400."""
        from todo.models.user import UserModel

        mock_user = Mock(spec=UserModel)
        mock_user.email_id = "test@example.com"
        mock_user_repo.return_value = mock_user

        response = self.client.get(f"{self.url}?task_id=invalid_id")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid task_id", response.data["message"])

    @patch("todo.repositories.watchlist_repository.WatchlistRepository.get_by_user_and_task")
    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    def test_check_task_in_watchlist_with_updated_by(self, mock_user_repo, mock_watchlist_repo):
        """Test that a task with updatedBy ObjectId works correctly."""
        from todo.models.user import UserModel

        mock_user = Mock(spec=UserModel)
        mock_user.email_id = "test@example.com"
        mock_user_repo.return_value = mock_user

        mock_watchlist_entry = Mock(spec=WatchlistModel)
        mock_watchlist_entry.isActive = True
        mock_watchlist_repo.return_value = mock_watchlist_entry

        response = self.client.get(f"{self.url}?task_id={self.task_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["in_watchlist"], True)
