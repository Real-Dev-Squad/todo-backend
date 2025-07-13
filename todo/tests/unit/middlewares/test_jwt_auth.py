from unittest import TestCase
from unittest.mock import Mock, patch
from django.http import HttpRequest, JsonResponse
from django.conf import settings
from rest_framework import status
import json
from todo.middlewares.jwt_auth import (
    JWTAuthenticationMiddleware,
    get_current_user_info,
)
from todo.constants.messages import AuthErrorMessages


class JWTAuthenticationMiddlewareTests(TestCase):
    def setUp(self):
        self.get_response = Mock(return_value=JsonResponse({"data": "test"}))
        self.middleware = JWTAuthenticationMiddleware(self.get_response)
        self.request = Mock(spec=HttpRequest)
        self.request.path = "/v1/tasks"
        self.request.headers = {}
        self.request.COOKIES = {}

    def test_public_path_authentication_bypass(self):
        """Test that requests to public paths bypass authentication"""
        self.request.path = "/v1/auth/google/login"
        response = self.middleware(self.request)
        self.get_response.assert_called_once_with(self.request)
        self.assertEqual(response.status_code, 200)

    @patch("todo.middlewares.jwt_auth.JWTAuthenticationMiddleware._try_authentication")
    def test_authentication_success(self, mock_auth):
        """Test successful authentication"""
        mock_auth.return_value = True
        self.request.COOKIES = {
            settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"): "valid_token"
        }
        response = self.middleware(self.request)
        mock_auth.assert_called_once_with(self.request)
        self.get_response.assert_called_once_with(self.request)
        self.assertEqual(response.status_code, 200)

    @patch("todo.middlewares.jwt_auth.validate_access_token")
    def test_access_token_validation_success(self, mock_validate):
        """Test successful access token validation"""
        mock_validate.return_value = {"user_id": "123", "token_type": "access"}
        self.request.COOKIES = {
            settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"): "valid_token"
        }
        self.assertEqual(self.request.user_id, "123")
        self.get_response.assert_called_once_with(self.request)

    @patch("todo.middlewares.jwt_auth.validate_access_token")
    @patch("todo.middlewares.jwt_auth.validate_refresh_token")
    @patch("todo.middlewares.jwt_auth.generate_access_token")
    def test_refresh_token_success(
        self, mock_generate, mock_validate_refresh, mock_validate_access
    ):
        """Test successful token refresh when access token is expired"""
        from todo.exceptions.auth_exceptions import TokenExpiredError

        mock_validate_access.side_effect = TokenExpiredError("Token expired")
        mock_validate_refresh.return_value = {"user_id": "123", "token_type": "refresh"}
        mock_generate.return_value = "new_access_token"

        self.request.COOKIES = {
            settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"): "expired_token",
            settings.COOKIE_SETTINGS.get("REFRESH_COOKIE_NAME"): "valid_refresh_token",
        }

        self.assertEqual(self.request.user_id, "123")
        self.assertEqual(self.request._new_access_token, "new_access_token")
        self.get_response.assert_called_once_with(self.request)

    def test_no_tokens_provided(self):
        """Test handling of request with no tokens"""
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = json.loads(response.content)
        self.assertEqual(
            response_data["message"], AuthErrorMessages.AUTHENTICATION_REQUIRED
        )


class AuthUtilityFunctionsTests(TestCase):
    def setUp(self):
        self.request = Mock(spec=HttpRequest)

    def test_get_current_user_info_with_user_id(self):
        """Test getting user info when user ID is present"""
        self.request.user_id = "user_123"
        user_info = get_current_user_info(self.request)
        self.assertEqual(user_info["user_id"], "user_123")

    def test_get_current_user_info_no_user_id(self):
        """Test getting user info when no user ID is present"""
        user_info = get_current_user_info(self.request)
        self.assertIsNone(user_info)
