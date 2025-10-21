from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timezone

from todo.constants.messages import ApiErrors
from todo.exceptions.team_exceptions import (
    CannotRemoveOwnerException,
    CannotRemoveTeamPOCException,
    NotTeamAdminException,
)
from todo.services.team_service import TeamService
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.common.pyobjectid import PyObjectId
from todo.dto.user_dto import UserDTO
from todo.dto.team_dto import TeamDTO
from todo.constants.role import RoleName, RoleScope


class TeamServiceTests(TestCase):
    def setUp(self):
        self.user_id = "507f1f77bcf86cd799439011"
        self.owner_id = "507f1f77bcf86cd799439011"
        self.admin_user_id = "507f1f77bcf86cd799439020"
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

        self.user_details = [
            UserDTO(id=self.user_id, name="Test User 1", addedOn=datetime.now(timezone.utc), tasksAssignedCount=2),
            UserDTO(id=self.poc_id, name="Test User 2", addedOn=datetime.now(timezone.utc), tasksAssignedCount=1),
            UserDTO(id=self.admin_id, name="Test User 3", addedOn=datetime.now(timezone.utc), tasksAssignedCount=2),
            UserDTO(id=self.member_id, name="Test User 4", addedOn=datetime.now(timezone.utc), tasksAssignedCount=1),
        ]

        self.team_details = TeamDTO(
            id=self.team_id,
            name="Test Team",
            description="Test Description",
            poc_id=self.poc_id,
            invite_code="TEST123",
            created_by=self.user_id,
            updated_by=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.user_model = UserDTO(
            id=self.member_id, name="Test User", addedOn=datetime.now(timezone.utc), tasksAssignedCount=0
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

    @patch("todo.services.user_service.UserService.get_users_by_team_id")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_cannot_remove_owner(self, mock_get_by_team_id, mock_get_users_by_team_id):
        """Test cannot remove team owner"""
        mock_get_users_by_team_id.return_value = self.user_details
        mock_get_by_team_id.return_value = self.team_details
        with self.assertRaises(CannotRemoveOwnerException):
            TeamService._validate_remove_member_permissions(self.user_id, self.team_id, self.user_id)

    @patch("todo.services.user_service.UserService.get_users_by_team_id")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_cannot_remove_poc(self, mock_get_by_team_id, mock_get_users_by_team_id):
        """Test cannot remove team POC"""
        mock_get_users_by_team_id.return_value = self.user_details
        mock_get_by_team_id.return_value = self.team_details

        with self.assertRaises(CannotRemoveTeamPOCException):
            TeamService._validate_remove_member_permissions(self.poc_id, self.team_id, self.user_id)

    @patch("todo.services.user_service.UserService.get_users_by_team_id")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_normal_member_cannot_remove_member(self, mock_get_by_team_id, mock_get_users_by_team_id):
        mock_get_users_by_team_id.return_value = self.user_details
        mock_get_by_team_id.return_value = self.team_details

        with self.assertRaises(NotTeamAdminException):
            TeamService._validate_remove_member_permissions(self.admin_id, self.team_id, self.member_id)

    @patch("todo.services.user_service.UserService.get_users_by_team_id")
    @patch("todo.services.team_service.TeamService.get_team_by_id")
    def test_team_or_user_not_found(self, mock_get_by_team_id, mock_get_users_by_team_id):
        mock_get_users_by_team_id.return_value = self.user_details
        mock_get_by_team_id.return_value = self.team_details

        with self.assertRaises(TeamService.TeamOrUserNotFound):
            TeamService._validate_remove_member_permissions("not-existing-member", self.team_id, self.member_id)

    @patch("todo.services.task_assignment_service.TaskAssignmentService.reassign_tasks_from_user_to_team")
    @patch("todo.services.user_role_service.UserRoleService.remove_all_user_roles_for_team")
    @patch("todo.repositories.audit_log_repository.AuditLogRepository.create")
    @patch("todo.repositories.user_team_details_repository.UserTeamDetailsRepository.remove_member_from_team")
    @patch("todo.services.team_service.TeamService._validate_remove_member_permissions")
    def test_admin_can_remove_member_successfully(
        self, mock_validate, mock_remove_member, mock_audit_log_create, mock_remove_roles, mock_reassign_tasks
    ):
        mock_validate.return_value = None
        mock_remove_member.return_value = True
        mock_remove_roles.return_value = True
        mock_reassign_tasks.return_value = True

        result = TeamService.remove_member_from_team(self.member_id, self.team_id, self.admin_id)

        self.assertTrue(result)
        mock_remove_member.assert_called_once_with(user_id=self.member_id, team_id=self.team_id)
        mock_remove_roles.assert_called_once()
        mock_reassign_tasks.assert_called_once()
        mock_audit_log_create.assert_called_once()
        log_entry = mock_audit_log_create.call_args[0][0]
        self.assertEqual(log_entry.action, "member_removed_from_team")
        self.assertEqual(str(log_entry.team_id), self.team_id)
        self.assertEqual(str(log_entry.performed_by), self.admin_id)

    @patch("todo.services.task_assignment_service.TaskAssignmentService.reassign_tasks_from_user_to_team")
    @patch("todo.services.user_role_service.UserRoleService.remove_all_user_roles_for_team")
    @patch("todo.repositories.audit_log_repository.AuditLogRepository.create")
    @patch("todo.repositories.user_team_details_repository.UserTeamDetailsRepository.remove_member_from_team")
    @patch("todo.services.team_service.TeamService._validate_remove_member_permissions")
    def test_user_can_remove_themselves(
        self, mock_validate, mock_remove_member, mock_audit_log_create, mock_remove_roles, mock_reassign_tasks
    ):
        mock_validate.return_value = None
        mock_remove_member.return_value = True
        mock_remove_roles.return_value = True
        mock_reassign_tasks.return_value = True

        result = TeamService.remove_member_from_team(self.member_id, self.team_id, self.member_id)

        self.assertTrue(result)
        mock_remove_member.assert_called_once_with(user_id=self.member_id, team_id=self.team_id)
        mock_remove_roles.assert_called_once_with(self.member_id, self.team_id)
        mock_reassign_tasks.assert_called_once_with(self.member_id, self.team_id, self.member_id)
        mock_audit_log_create.assert_called_once()
        log_entry = mock_audit_log_create.call_args[0][0]
        self.assertEqual(log_entry.action, "member_left_team")
        self.assertEqual(str(log_entry.team_id), self.team_id)
        self.assertEqual(str(log_entry.performed_by), self.member_id)

    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_validate_is_team_admin_success(self, mock_has_role):
        mock_has_role.return_value = True

        result = TeamService._validate_is_user_team_admin(self.team_id, self.admin_id, self.team_model)
        self.assertIsNone(result)
        mock_has_role.assert_called_once_with(self.admin_id, RoleName.ADMIN.value, RoleScope.TEAM.value, self.team_id)

    def test_validate_is_team_admin_success_for_owner(self):
        result = TeamService._validate_is_user_team_admin(self.team_id, self.owner_id, self.team_model)
        self.assertIsNone(result)

    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_validate_is_team_admin_fails_for_regular_member(self, mock_has_role):
        mock_has_role.return_value = False

        with self.assertRaises(PermissionError) as context:
            TeamService._validate_is_user_team_admin(self.team_id, self.member_id, self.team_model)

        self.assertIn(ApiErrors.UNAUTHORIZED_TITLE, str(context.exception))
        mock_has_role.assert_called_once_with(self.member_id, RoleName.ADMIN.value, RoleScope.TEAM.value, self.team_id)

    @patch("todo.dto.update_team_dto.UserRepository.get_by_id")
    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.TeamRepository.update")
    @patch("todo.services.team_service.AuditLogRepository.create")
    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_update_team_success_by_admin(
        self, mock_has_role, mock_audit_log_create, mock_team_update, mock_team_get, mock_user_get
    ):
        mock_team_get.return_value = self.team_model
        mock_team_update.return_value = self.team_model
        mock_has_role.return_value = True
        mock_user_get.return_value = UserDTO(
            id=self.member_id, name="Test User", addedOn=datetime.now(timezone.utc), tasksAssignedCount=1
        )

        result = TeamService.update_team(
            team_id=self.team_id,
            poc_id=self.member_id,
            user_id=self.admin_id,
        )

        self.assertIsInstance(result, TeamDTO)
        mock_team_get.assert_called_once_with(self.team_id)
        mock_team_update.assert_called_once()
        mock_audit_log_create.assert_called_once()
        self.assertEqual(mock_has_role.call_count, 2)
        mock_has_role.assert_any_call(self.admin_id, RoleName.ADMIN.value, RoleScope.TEAM.value, self.team_id)
        mock_has_role.assert_any_call(self.member_id, RoleName.MEMBER.value, RoleScope.TEAM.value, self.team_id)

    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.TeamRepository.update")
    @patch("todo.services.team_service.AuditLogRepository.create")
    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_update_team_success_by_owner(
        self, mock_has_role, mock_user_get, mock_audit_log_create, mock_team_update, mock_team_get
    ):
        mock_team_get.return_value = self.team_model
        mock_team_update.return_value = self.team_model
        mock_user_get.return_value = self.user_model
        mock_has_role.return_value = True

        result = TeamService.update_team(
            team_id=self.team_id,
            poc_id=self.member_id,
            user_id=self.owner_id,
        )

        self.assertIsInstance(result, TeamDTO)
        mock_team_get.assert_called_once_with(self.team_id)
        mock_team_update.assert_called_once()
        mock_audit_log_create.assert_called_once()

    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_update_team_fails_for_non_admin(self, mock_has_role, mock_team_get):
        mock_team_get.return_value = self.team_model
        mock_has_role.return_value = False

        with self.assertRaises(PermissionError) as context:
            TeamService.update_team(team_id=self.team_id, poc_id=self.member_id, user_id=self.member_id)

        self.assertIn(ApiErrors.UNAUTHORIZED_TITLE, str(context.exception))
        mock_has_role.assert_called_once_with(self.member_id, RoleName.ADMIN.value, RoleScope.TEAM.value, self.team_id)

    @patch("todo.dto.update_team_dto.UserRepository.get_by_id")
    @patch("todo.services.team_service.TeamRepository.update")
    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_update_team_poc_not_team_member_raises_error(
        self, mock_has_role, mock_team_get, mock_team_update, mock_user_get
    ):
        mock_team_get.return_value = self.team_model
        mock_team_update.return_value = self.team_model
        mock_user_get.return_value = UserDTO(
            id=self.member_id, name="Test User", addedOn=datetime.now(timezone.utc), tasksAssignedCount=1
        )
        mock_has_role.side_effect = [True, False]

        result = TeamService.update_team(team_id=self.team_id, poc_id=self.member_id, user_id=self.admin_user_id)

        self.assertIsNotNone(result)
        self.assertIn("User is not a member of the team", str(result))
        self.assertEqual(mock_has_role.call_count, 2)
        mock_has_role.assert_any_call(self.member_id, RoleName.MEMBER.value, RoleScope.TEAM.value, self.team_id)

    @patch("todo.services.team_service.TeamRepository.get_by_id")
    @patch("todo.services.team_service.TeamRepository.update")
    @patch("todo.services.team_service.AuditLogRepository.create")
    @patch("todo.repositories.user_repository.UserRepository.get_by_id")
    @patch("todo.services.team_service.UserRoleService.has_role")
    def test_update_team_creates_poc_changed_audit_log(
        self, mock_has_role, mock_user_get, mock_audit_log_create, mock_team_update, mock_team_get
    ):
        mock_team_get.return_value = self.team_model
        mock_team_update.return_value = self.team_model
        mock_user_get.return_value = self.user_model
        mock_has_role.return_value = True

        TeamService.update_team(
            team_id=self.team_id,
            poc_id=self.member_id,
            user_id=self.owner_id,
        )

        mock_audit_log_create.assert_called_once()

        audit_log_model = mock_audit_log_create.call_args[0][0]

        self.assertEqual(audit_log_model.action, "poc_changed")
        self.assertEqual(audit_log_model.team_id, PyObjectId(self.team_id))
        self.assertEqual(audit_log_model.performed_by, PyObjectId(self.owner_id))
