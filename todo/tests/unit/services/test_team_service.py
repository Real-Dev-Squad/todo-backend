from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timezone

from todo.exceptions.team_exceptions import (
    CannotRemoveOwnerException,
    CannotRemoveTeamPOCException,
    NotTeamAdminException,
)
from todo.services.team_service import TeamService
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.user_role import UserRoleModel
from todo.models.common.pyobjectid import PyObjectId
from todo.constants.role import RoleName, RoleScope


class TeamServiceTests(TestCase):
    def setUp(self):
        self.user_id = "507f1f77bcf86cd799439011"
        self.team_id = "507f1f77bcf86cd799439012"
        self.poc_id = "507f1f77bcf86cd799439014"
        self.admin_id = "507f1f77bcf86cd799439015"
        self.member_id = "507f1f77bcf86cd799439016"
        # Mock team model
        self.team_model = TeamModel(
            id=PyObjectId(self.team_id),
            name="Test Team",
            description="Test Description",
            poc_id=PyObjectId(self.poc_id),
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

        # Mock user roles
        self.owner_roles = [
            UserRoleModel(
                id=PyObjectId("507f1f77bcf86cd799439021"),
                user_id=self.user_id,
                role_name=RoleName.ADMIN,
                scope=RoleScope.TEAM,
                team_id=self.team_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                created_by="system",
            ),
            UserRoleModel(
                id=PyObjectId("507f1f77bcf86cd799439022"),
                user_id=self.user_id,
                role_name=RoleName.OWNER,
                scope=RoleScope.TEAM,
                team_id=self.team_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                created_by="system",
            ),
            UserRoleModel(
                id=PyObjectId("507f1f77bcf86cd799439023"),
                user_id=self.user_id,
                role_name=RoleName.MEMBER,
                scope=RoleScope.TEAM,
                team_id=self.team_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                created_by="system",
            ),
        ]

        self.poc_roles = UserRoleModel(
            id=PyObjectId("507f1f77bcf86cd799439031"),
            user_id=self.poc_id,
            role_name=RoleName.MEMBER,
            scope=RoleScope.TEAM,
            team_id=self.team_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            created_by="system",
        )

        self.admin_roles = [
            UserRoleModel(
                id=PyObjectId("507f1f77bcf86cd799439041"),
                user_id=self.admin_id,
                role_name=RoleName.ADMIN,
                scope=RoleScope.TEAM,
                team_id=self.team_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                created_by="system",
            ),
            UserRoleModel(
                id=PyObjectId("507f1f77bcf86cd799439042"),
                user_id=self.admin_id,
                role_name=RoleName.MEMBER,
                scope=RoleScope.TEAM,
                team_id=self.team_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                created_by="system",
            ),
        ]

        self.member_roles = [
            {
                "role_id": "507f1f77bcf86cd799439051",
                "role_name": RoleName.MEMBER,
                "scope": RoleScope.TEAM,
                "team_id": self.team_id,
                "assigned_at": datetime.now(timezone.utc),
            }
        ]

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

    @patch("todo.services.user_role_service.UserRoleService.assign_role")
    @patch("todo.services.team_service.AuditLogRepository.create")
    @patch("todo.services.team_service.TeamCreationInviteCodeRepository.validate_and_consume_code")
    @patch("todo.services.team_service.TeamRepository.create")
    @patch("todo.services.team_service.UserTeamDetailsRepository.create_many")
    @patch("todo.dto.team_dto.UserRepository.get_by_id")
    def test_creator_always_added_as_member(
        self,
        mock_user_get_by_id,
        mock_create_many,
        mock_team_create,
        mock_validate_and_consume_code,
        mock_audit_log_create,
        mock_assign_role,
    ):
        """Test that the creator is always added as a member when creating a team"""
        # Patch user lookup to always return a mock user
        mock_user = type(
            "User",
            (),
            {"id": None, "name": "Test User", "email_id": "test@example.com", "created_at": None, "updated_at": None},
        )()
        mock_user_get_by_id.return_value = mock_user

        mock_validate_and_consume_code.return_value = {"_id": "507f1f77bcf86cd799439013"}
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

    @patch("todo.services.user_role_service.UserRoleService.assign_role")
    @patch("todo.services.team_service.AuditLogRepository.create")
    @patch("todo.services.team_service.TeamRepository.get_by_invite_code")
    @patch("todo.services.team_service.UserTeamDetailsRepository.get_by_user_id")
    @patch("todo.services.team_service.UserTeamDetailsRepository.create")
    def test_join_team_by_invite_code_success(
        self, mock_create, mock_get_by_user_id, mock_get_by_invite_code, mock_audit_log_create, mock_assign_role
    ):
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

    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_cannot_remove_owner(self, mock_get_by_team_id):
        """Test cannot remove team owner"""
        mock_get_by_team_id.return_value = self.team_model

        with self.assertRaises(CannotRemoveOwnerException):
            TeamService.remove_member_from_team(PyObjectId(self.user_id), self.team_id, self.user_id)

    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_cannot_remove_poc(self, mock_get_by_team_id):
        """Test cannot remove team POC"""
        mock_get_by_team_id.return_value = self.team_model

        with self.assertRaises(CannotRemoveTeamPOCException):
            TeamService.remove_member_from_team(self.team_model.poc_id, self.team_id, self.user_id)

    @patch("todo.services.user_role_service.UserRoleService.has_role")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_normal_member_cannot_remove_member(self, mock_get_by_team_id, mock_has_role):
        mock_get_by_team_id.return_value = self.team_model
        mock_has_role.return_value = False

        with self.assertRaises(NotTeamAdminException):
            TeamService.remove_member_from_team(self.admin_id, self.team_id, self.member_id)

    @patch("todo.services.user_role_service.UserRoleService.has_role")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_team_or_user_not_found(self, mock_get_by_team_id, mock_has_role):
        mock_get_by_team_id.return_value = self.team_model
        mock_has_role.return_value = False

        with self.assertRaises(TeamService.TeamOrUserNotFound):
            TeamService.remove_member_from_team(self.member_id, "not-teamid-exist", self.member_id)

    @patch("todo.repositories.audit_log_repository.AuditLogRepository.create")
    @patch("todo.services.task_assignment_service.TaskAssignmentService.reassign_tasks_from_user_to_team")
    @patch("todo.services.user_role_service.UserRoleService.remove_role_by_id")
    @patch("todo.repositories.user_team_details_repository.UserTeamDetailsRepository.remove_member_from_team")
    @patch("todo.services.user_role_service.UserRoleService.get_user_roles")
    @patch("todo.services.user_role_service.UserRoleService.has_role")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_admin_can_remove_member_successfully(
        self,
        mock_get_by_team_id,
        mock_has_role,
        mock_get_user_roles,
        mock_remove_member_from_team,
        mock_remove_role_by_id,
        mock_reassign_tasks_from_user_to_team,
        mock_audit_log_create,
    ):
        mock_get_by_team_id.return_value = self.team_model
        mock_has_role.return_value = True
        mock_get_user_roles.return_value = self.member_roles

        result = TeamService.remove_member_from_team(self.member_id, self.team_id, self.admin_id)

        self.assertTrue(result)

    @patch("todo.repositories.audit_log_repository.AuditLogRepository.create")
    @patch("todo.services.task_assignment_service.TaskAssignmentService.reassign_tasks_from_user_to_team")
    @patch("todo.services.user_role_service.UserRoleService.remove_role_by_id")
    @patch("todo.repositories.user_team_details_repository.UserTeamDetailsRepository.remove_member_from_team")
    @patch("todo.services.user_role_service.UserRoleService.get_user_roles")
    @patch("todo.services.user_role_service.UserRoleService.has_role")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_user_can_remove_themself(
        self,
        mock_get_by_team_id,
        mock_has_role,
        mock_get_user_roles,
        mock_remove_member_from_team,
        mock_remove_role_by_id,
        mock_reassign_tasks_from_user_to_team,
        mock_audit_log_create,
    ):
        mock_get_by_team_id.return_value = self.team_model
        mock_has_role.return_value = True
        mock_get_user_roles.return_value = self.member_roles

        result = TeamService.remove_member_from_team(self.member_id, self.team_id, self.member_id)

        self.assertTrue(result)
