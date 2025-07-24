from unittest import TestCase
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status

from todo.views.team import TeamListView, JoinTeamByInviteCodeView, RemoveTeamMemberView
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.dto.team_dto import TeamDTO
from datetime import datetime, timezone


class TeamListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.view = TeamListView()
        self.mock_user_id = "507f1f77bcf86cd799439011"

    @patch("todo.views.team.TeamService.get_user_teams")
    def test_get_user_teams_success(self, mock_get_user_teams):
        """Test successful retrieval of user teams"""
        # Mock team data
        team_dto = TeamDTO(
            id="507f1f77bcf86cd799439012",
            name="Test Team",
            description="Test Description",
            poc_id="507f1f77bcf86cd799439013",
            invite_code="TEST123",
            created_by="507f1f77bcf86cd799439011",
            updated_by="507f1f77bcf86cd799439011",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_response = GetUserTeamsResponse(teams=[team_dto], total=1)
        mock_get_user_teams.return_value = mock_response

        # Mock request with user_id
        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id

        response = self.view.get(mock_request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_user_teams.assert_called_once_with(self.mock_user_id)

        # Check response data
        response_data = response.data
        self.assertEqual(response_data["total"], 1)
        self.assertEqual(len(response_data["teams"]), 1)
        self.assertEqual(response_data["teams"][0]["name"], "Test Team")

    @patch("todo.views.team.TeamService.get_user_teams")
    def test_get_user_teams_empty_result(self, mock_get_user_teams):
        """Test when user has no teams"""
        mock_response = GetUserTeamsResponse(teams=[], total=0)
        mock_get_user_teams.return_value = mock_response

        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id

        response = self.view.get(mock_request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.data
        self.assertEqual(response_data["total"], 0)
        self.assertEqual(len(response_data["teams"]), 0)

    @patch("todo.views.team.TeamService.get_user_teams")
    def test_get_user_teams_service_error(self, mock_get_user_teams):
        """Test when service throws an error"""
        mock_get_user_teams.side_effect = ValueError("Service error")

        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id

        response = self.view.get(mock_request)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        response_data = response.data
        self.assertEqual(response_data["statusCode"], 500)


class JoinTeamByInviteCodeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.view = JoinTeamByInviteCodeView()
        self.mock_user_id = "507f1f77bcf86cd799439011"

    @patch("todo.views.team.TeamService.join_team_by_invite_code")
    def test_join_team_by_invite_code_success(self, mock_join):
        team_dto = TeamDTO(
            id="507f1f77bcf86cd799439012",
            name="Test Team",
            description="Test Description",
            poc_id="507f1f77bcf86cd799439013",
            invite_code="TEST123",
            created_by="507f1f77bcf86cd799439011",
            updated_by="507f1f77bcf86cd799439011",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_join.return_value = team_dto
        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id
        mock_request.data = {"invite_code": "TEST123"}
        response = self.view.post(mock_request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Team")

    @patch("todo.views.team.TeamService.join_team_by_invite_code")
    def test_join_team_by_invite_code_invalid_code(self, mock_join):
        mock_join.side_effect = ValueError("Invalid invite code or team does not exist.")
        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id
        mock_request.data = {"invite_code": "INVALID"}
        response = self.view.post(mock_request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid invite code", response.data["detail"])

    @patch("todo.views.team.TeamService.join_team_by_invite_code")
    def test_join_team_by_invite_code_already_member(self, mock_join):
        mock_join.side_effect = ValueError("User is already a member of this team.")
        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id
        mock_request.data = {"invite_code": "TEST123"}
        response = self.view.post(mock_request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already a member", response.data["detail"])

    def test_join_team_by_invite_code_validation_error(self):
        mock_request = MagicMock()
        mock_request.user_id = self.mock_user_id
        mock_request.data = {"invite_code": ""}  # Empty code
        response = self.view.post(mock_request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invite_code", response.data)


class RemoveTeamMemberViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.team_id = "507f1f77bcf86cd799439012"
        self.user_id = "507f1f77bcf86cd799439011"
        self.url = f"/teams/{self.team_id}/members/{self.user_id}/"

    @patch("todo.views.team.TeamService.remove_member_from_team")
    def test_remove_member_success(self, mock_remove):
        mock_remove.return_value = True
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_remove.assert_called_once_with(user_id=self.user_id, team_id=self.team_id)

    @patch("todo.views.team.TeamService.remove_member_from_team")
    def test_remove_member_not_found(self, mock_remove):
        from todo.services.team_service import TeamService
        mock_remove.side_effect = TeamService.TeamOrUserNotFound()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.data["detail"])

    @patch("todo.views.team.TeamService.remove_member_from_team")
    def test_remove_member_generic_error(self, mock_remove):
        mock_remove.side_effect = Exception("Something went wrong")
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Something went wrong", response.data["detail"])
