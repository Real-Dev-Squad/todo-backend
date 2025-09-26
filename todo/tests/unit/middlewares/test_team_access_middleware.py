from unittest import TestCase
from unittest.mock import Mock, patch
from django.http import HttpRequest, JsonResponse
from rest_framework import status
import json

from todo.middlewares.team_access_middleware import TeamAccessMiddleware
from todo.constants.messages import ApiErrors


class TeamAccessMiddlewareTests(TestCase):
    def setUp(self):
        self.get_response = Mock(return_value=JsonResponse({"data": "success"}))
        self.middleware = TeamAccessMiddleware(self.get_response)
        self.request = Mock(spec=HttpRequest)
        self.request.user_id = "user123"
        self.request.path_info = "/v1/teams/team123"

    @patch("todo.middlewares.team_access_middleware.resolve")
    def test_protected_route_with_valid_access(self, mock_resolve):
        mock_resolve.return_value.url_name = "team_detail"
        mock_resolve.return_value.kwargs = {"team_id": "team123"}

        with patch("todo.middlewares.team_access_middleware.UserRoleService.get_user_roles") as mock_get_roles:
            mock_get_roles.return_value = [{"role": "admin"}]

            response = self.middleware(self.request)

            self.assertEqual(response.status_code, 200)
            self.get_response.assert_called_once_with(self.request)

    @patch("todo.middlewares.team_access_middleware.resolve")
    def test_protected_route_with_no_access(self, mock_resolve):
        mock_resolve.return_value.url_name = "team_detail"
        mock_resolve.return_value.kwargs = {"team_id": "team123"}

        with patch("todo.middlewares.team_access_middleware.UserRoleService.get_user_roles") as mock_get_roles:
            mock_get_roles.return_value = []

            response = self.middleware(self.request)

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response_data = json.loads(response.content)
            self.assertEqual(response_data["detail"], ApiErrors.UNAUTHORIZED_TITLE)

    @patch("todo.middlewares.team_access_middleware.resolve")
    def test_unprotected_route_bypasses_middleware(self, mock_resolve):
        mock_resolve.return_value.url_name = "task_list"
        mock_resolve.return_value.kwargs = {}

        response = self.middleware(self.request)

        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_once_with(self.request)

    @patch("todo.middlewares.team_access_middleware.resolve")
    def test_middleware_handles_exception_with_500(self, mock_resolve):
        mock_resolve.return_value.url_name = "team_detail"
        mock_resolve.return_value.kwargs = {"team_id": "team123"}

        with patch("todo.middlewares.team_access_middleware.UserRoleService.get_user_roles") as mock_get_roles:
            mock_get_roles.side_effect = Exception("Database connection failed")

            response = self.middleware(self.request)

            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            response_data = json.loads(response.content)
            self.assertEqual(response_data["detail"], ApiErrors.INTERNAL_SERVER_ERROR)

    @patch("todo.middlewares.team_access_middleware.resolve")
    def test_missing_team_id_returns_400(self, mock_resolve):
        mock_resolve.return_value.url_name = "team_detail"
        mock_resolve.return_value.kwargs = {}

        response = self.middleware(self.request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["detail"], "Team ID is required.")
