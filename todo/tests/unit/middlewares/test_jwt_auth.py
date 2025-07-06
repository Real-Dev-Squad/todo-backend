from unittest import TestCase
from unittest.mock import Mock, patch
from django.http import HttpRequest, JsonResponse
from rest_framework import status
import json

from todo.middlewares.jwt_auth import JWTAuthenticationMiddleware, is_google_user, is_rds_user, get_current_user_info
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

    @patch("todo.middlewares.jwt_auth.JWTAuthenticationMiddleware._try_google_auth")
    def test_google_auth_success(self, mock_google_auth):
        """Test successful Google authentication"""
        mock_google_auth.return_value = True
        self.request.COOKIES = {"ext-access": "google_token"}
        response = self.middleware(self.request)
        mock_google_auth.assert_called_once_with(self.request)
        self.get_response.assert_called_once_with(self.request)
        self.assertEqual(response.status_code, 200)

    @patch("todo.middlewares.jwt_auth.JWTAuthenticationMiddleware._try_rds_auth")
    def test_rds_auth_success(self, mock_rds_auth):
        """Test successful RDS authentication"""
        mock_rds_auth.return_value = True
        self.request.COOKIES = {"rds_session_v2": "valid_token"}
        response = self.middleware(self.request)
        mock_rds_auth.assert_called_once_with(self.request)
        self.get_response.assert_called_once_with(self.request)
        self.assertEqual(response.status_code, 200)

    @patch("todo.middlewares.jwt_auth.JWTAuthenticationMiddleware._try_google_auth")
    def test_google_token_expired(self, mock_google_auth):
        """Test handling of expired Google token"""
        mock_google_auth.return_value = False
        self.request.COOKIES = {"ext-access": "expired_token"}
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["message"], AuthErrorMessages.AUTHENTICATION_REQUIRED)

    @patch("todo.middlewares.jwt_auth.JWTAuthenticationMiddleware._try_rds_auth")
    def test_rds_token_invalid(self, mock_rds_auth):
        """Test handling of invalid RDS token"""
        mock_rds_auth.return_value = False
        self.request.COOKIES = {"rds_session_v2": "invalid_token"}
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["message"], AuthErrorMessages.AUTHENTICATION_REQUIRED)

    def test_no_tokens_provided(self):
        """Test handling of request with no tokens"""
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["message"], AuthErrorMessages.AUTHENTICATION_REQUIRED)


class AuthUtilityFunctionsTests(TestCase):
    def setUp(self):
        self.request = Mock(spec=HttpRequest)

    def test_is_google_user(self):
        """Test checking if request is from Google user"""
        self.request.auth_type = "google"
        self.assertTrue(is_google_user(self.request))

        self.request.auth_type = None
        self.assertFalse(is_google_user(self.request))

        self.request.auth_type = "rds"
        self.assertFalse(is_google_user(self.request))

    def test_is_rds_user(self):
        """Test checking if request is from RDS user"""
        self.request.auth_type = "rds"
        self.assertTrue(is_rds_user(self.request))

        self.request.auth_type = None
        self.assertFalse(is_rds_user(self.request))

        self.request.auth_type = "google"
        self.assertFalse(is_rds_user(self.request))

    def test_get_current_user_info_google(self):
        """Test getting user info for Google user"""
        self.request.user_id = "google_user_123"
        self.request.auth_type = "google"
        self.request.google_id = "google_123"
        self.request.user_email = "test@example.com"
        self.request.user_name = "Test User"
        user_info = get_current_user_info(self.request)
        self.assertEqual(user_info["user_id"], "google_user_123")
        self.assertEqual(user_info["auth_type"], "google")
        self.assertEqual(user_info["google_id"], "google_123")
        self.assertEqual(user_info["email"], "test@example.com")
        self.assertEqual(user_info["name"], "Test User")

    def test_get_current_user_info_rds(self):
        """Test getting user info for RDS user"""
        self.request.user_id = "rds_user_123"
        self.request.auth_type = "rds"
        self.request.user_role = "admin"
        user_info = get_current_user_info(self.request)
        self.assertEqual(user_info["user_id"], "rds_user_123")
        self.assertEqual(user_info["auth_type"], "rds")
        self.assertEqual(user_info["role"], "admin")

    def test_get_current_user_info_no_user_id(self):
        """Test getting user info when no user ID is present"""
        user_info = get_current_user_info(self.request)
        self.assertIsNone(user_info)
