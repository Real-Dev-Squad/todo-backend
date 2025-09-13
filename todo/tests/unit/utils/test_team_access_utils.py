from unittest.mock import Mock, patch
from django.test import TestCase
from rest_framework.response import Response

from todo.utils.team_access import has_team_access, team_access_required
from todo.constants.role import RoleScope


class TestTeamAccessUtils(TestCase):
    def setUp(self):
        self.user_id = "user123"
        self.team_id = "team456"
        self.team_data = Mock()
        self.team_data.poc_id = "other_user"
        self.team_data.created_by = "other_creator"

    @patch("todo.utils.team_access.TeamRepository.get_by_id")
    @patch("todo.utils.team_access.UserRoleService.get_user_roles")
    def test_has_team_access_no_role_no_poc_no_creator(self, mock_get_roles, mock_get_team):
        mock_get_roles.return_value = []
        mock_get_team.return_value = self.team_data

        result = has_team_access(self.user_id, self.team_id)

        self.assertFalse(result)
        mock_get_roles.assert_called_once_with(user_id=self.user_id, scope=RoleScope.TEAM.value, team_id=self.team_id)
        mock_get_team.assert_called_once_with(self.team_id)

    @patch("todo.utils.team_access.TeamRepository.get_by_id")
    @patch("todo.utils.team_access.UserRoleService.get_user_roles")
    def test_has_team_access_team_not_found(self, mock_get_roles, mock_get_team):
        mock_get_roles.return_value = []
        mock_get_team.return_value = None

        result = has_team_access(self.user_id, self.team_id)

        self.assertFalse(result)

    @patch("todo.utils.team_access.has_team_access")
    def test_team_access_required_decorator_denies_access(self, mock_has_access):
        mock_has_access.return_value = False

        class TestView:
            @team_access_required
            def test_method(self, request, team_id):
                return "success"

        request = Mock()
        request.user_id = self.user_id

        view = TestView()
        result = view.test_method(request, team_id=self.team_id)

        self.assertIsInstance(result, Response)
        self.assertEqual(result.status_code, 403)
        self.assertIn("not authorized", result.data["detail"].lower())
        mock_has_access.assert_called_once_with(self.user_id, self.team_id)

    @patch("todo.utils.team_access.UserRoleService.get_user_roles")
    def test_has_team_access_exception_handling(self, mock_get_roles):
        mock_get_roles.side_effect = Exception("Database error")

        result = has_team_access(self.user_id, self.team_id)

        self.assertFalse(result)
