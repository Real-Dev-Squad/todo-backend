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

    @patch("todo.services.team_service.TeamCreationInviteCodeRepository.consume_code")
    @patch("todo.services.team_service.TeamCreationInviteCodeRepository.is_code_valid")
    @patch("todo.services.team_service.TeamRepository.create")
    @patch("todo.services.team_service.UserTeamDetailsRepository.create_many")
    @patch("todo.dto.team_dto.UserRepository.get_by_id")
    def test_creator_always_added_as_member(
        self, mock_user_get_by_id, mock_create_many, mock_team_create, mock_is_code_valid, mock_consume_code
    ):
        """Test that the creator is always added as a member when creating a team"""
        # Patch user lookup to always return a mock user
        mock_user = type(
            "User",
            (),
            {"id": None, "name": "Test User", "email_id": "test@example.com", "created_at": None, "updated_at": None},
        )()
        mock_user_get_by_id.return_value = mock_user

        # Mock invite code validation
        mock_is_code_valid.return_value = {"_id": "507f1f77bcf86cd799439013"}
        mock_consume_code.return_value = True
        # Creator is not in member_ids or as POC
        creator_id = "507f1f77bcf86cd799439099"
        member_ids = ["507f1f77bcf86cd799439011"]
        poc_id = "507f1f77bcf86cd799439012"
        from todo.dto.team_dto import CreateTeamDTO

        dto = CreateTeamDTO(
            name="Team With Creator",
            description="desc",
            member_ids=member_ids,
            poc_id=poc_id,
            team_invite_code="TEST123",
        )
        # Mock team creation
        mock_team = self.team_model
        mock_team_create.return_value = mock_team
        # Call create_team
        TeamService.create_team(dto, creator_id)
        # Check that creator_id is in the user_team relationships
        user_team_objs = mock_create_many.call_args[0][0]
        all_user_ids = [str(obj.user_id) for obj in user_team_objs]
        self.assertIn(creator_id, all_user_ids)

    @patch("todo.services.team_service.TeamRepository.get_by_invite_code")
    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    @patch("todo.services.team_service.UserTeamDetailsRepository.create")
    def test_join_team_by_invite_code_success(self, mock_create, mock_get_by_user_id, mock_get_by_invite_code):
        """Test successful join by invite code"""
        mock_get_by_invite_code.return_value = self.team_model
        mock_get_by_user_id.return_value = []  # Not a member yet
        mock_create.return_value = self.user_team_details

        from todo.services.team_service import TeamService

        team_dto = TeamService.join_team_by_invite_code("TEST123", self.user_id)
        self.assertEqual(team_dto.id, self.team_id)
        self.assertEqual(team_dto.name, "Test Team")
        mock_get_by_invite_code.assert_called_once_with("TEST123")
        mock_create.assert_called_once()

    @patch("todo.services.team_service.TeamRepository.get_by_invite_code")
    def test_join_team_by_invite_code_invalid_code(self, mock_get_by_invite_code):
        """Test join by invite code with invalid code"""
        mock_get_by_invite_code.return_value = None
        from todo.services.team_service import TeamService

        with self.assertRaises(ValueError) as context:
            TeamService.join_team_by_invite_code("INVALID", self.user_id)
        self.assertIn("Invalid invite code", str(context.exception))

    @patch("todo.services.team_service.TeamRepository.get_by_invite_code")
    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    def test_join_team_by_invite_code_already_member(self, mock_get_by_user_id, mock_get_by_invite_code):
        """Test join by invite code when already a member"""
        mock_get_by_invite_code.return_value = self.team_model
        mock_get_by_user_id.return_value = [self.user_team_details]  # Already a member
        from todo.services.team_service import TeamService

        with self.assertRaises(ValueError) as context:
            TeamService.join_team_by_invite_code("TEST123", self.user_id)
        self.assertIn("already a member", str(context.exception))
