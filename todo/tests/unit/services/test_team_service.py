from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timezone

from todo.services.team_service import TeamService
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.common.pyobjectid import PyObjectId


class TeamServiceTests(TestCase):
    def setUp(self):
        self.user_id = "507f1f77bcf86cd799439011"
        self.team_id = "507f1f77bcf86cd799439012"

        # Mock team model
        self.team_model = TeamModel(
            id=PyObjectId(self.team_id),
            name="Test Team",
            description="Test Description",
            poc_id=PyObjectId(self.user_id),
            invite_code="TEST123",
            created_by=PyObjectId(self.user_id),
            updated_by=PyObjectId(self.user_id),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock user team details model
        self.user_team_details = UserTeamDetailsModel(
            id=PyObjectId("507f1f77bcf86cd799439013"),
            user_id=PyObjectId(self.user_id),
            team_id=PyObjectId(self.team_id),
            role_id="1",
            is_active=True,
            created_by=PyObjectId(self.user_id),
            updated_by=PyObjectId(self.user_id),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    def test_get_user_teams_success(self, mock_get_by_user_id, mock_get_team_by_id):
        """Test successful retrieval of user teams"""
        # Mock repository responses
        mock_get_by_user_id.return_value = [self.user_team_details]
        mock_get_team_by_id.return_value = self.team_model

        # Call service method
        response = TeamService.get_user_teams(self.user_id)

        # Assertions
        self.assertIsInstance(response, GetUserTeamsResponse)
        self.assertEqual(response.total, 1)
        self.assertEqual(len(response.teams), 1)
        self.assertEqual(response.teams[0].name, "Test Team")
        self.assertEqual(response.teams[0].id, self.team_id)

        # Verify repository calls
        mock_get_by_user_id.assert_called_once_with(self.user_id)
        mock_get_team_by_id.assert_called_once_with(self.team_id)

    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    def test_get_user_teams_no_teams(self, mock_get_by_user_id):
        """Test when user has no teams"""
        mock_get_by_user_id.return_value = []

        response = TeamService.get_user_teams(self.user_id)

        self.assertIsInstance(response, GetUserTeamsResponse)
        self.assertEqual(response.total, 0)
        self.assertEqual(len(response.teams), 0)

    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    def test_get_user_teams_team_not_found(self, mock_get_by_user_id, mock_get_team_by_id):
        """Test when team is not found for user team relationship"""
        mock_get_by_user_id.return_value = [self.user_team_details]
        mock_get_team_by_id.return_value = None  # Team not found

        response = TeamService.get_user_teams(self.user_id)

        self.assertIsInstance(response, GetUserTeamsResponse)
        self.assertEqual(response.total, 0)
        self.assertEqual(len(response.teams), 0)

    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    def test_get_user_teams_repository_error(self, mock_get_by_user_id):
        """Test when repository throws an exception"""
        mock_get_by_user_id.side_effect = Exception("Database error")

        with self.assertRaises(ValueError) as context:
            TeamService.get_user_teams(self.user_id)

        self.assertIn("Failed to get user teams", str(context.exception))
