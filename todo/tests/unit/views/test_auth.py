from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from rest_framework.reverse import reverse
from rest_framework import status
from unittest.mock import patch, Mock, PropertyMock
from bson.objectid import ObjectId

from todo.views.auth import (
    GoogleCallbackView,
)

from todo.utils.google_jwt_utils import (
    generate_google_token_pair,
)
from todo.constants.messages import AppMessages, AuthErrorMessages


class GoogleLoginViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_login")

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_returns_redirect_url_for_html_request(self, mock_get_auth_url):
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, mock_auth_url)
        mock_get_auth_url.assert_called_once_with(None)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_returns_json_for_json_request(self, mock_get_auth_url):
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)

        response = self.client.get(self.url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["authUrl"], mock_auth_url)
        self.assertEqual(response.data["data"]["state"], mock_state)
        mock_get_auth_url.assert_called_once_with(None)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_with_redirect_url(self, mock_get_auth_url):
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)
        redirect_url = "http://localhost:3000/callback"

        response = self.client.get(f"{self.url}?redirectURL={redirect_url}")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, mock_auth_url)
        mock_get_auth_url.assert_called_once_with(redirect_url)


class GoogleCallbackViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_callback")
        self.factory = APIRequestFactory()
        self.view = GoogleCallbackView.as_view()

    def test_get_redirects_for_oauth_error(self):
        error = "access_denied"
        response = self.client.get(f"{self.url}?error={error}")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=access_denied", response.url)

    def test_get_redirects_for_missing_code(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=missing_code", response.url)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.handle_callback")
    @patch("todo.services.user_service.UserService.create_or_update_user")
    def test_get_redirects_for_valid_code_and_state(self, mock_create_user, mock_handle_callback):
        mock_google_data = {
            "id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        user_id = str(ObjectId())
        mock_user = Mock()
        mock_user.id = ObjectId(user_id)
        mock_user.google_id = mock_google_data["id"]
        mock_user.email_id = mock_google_data["email"]
        mock_user.name = mock_google_data["name"]
        type(mock_user).id = PropertyMock(return_value=ObjectId(user_id))

        mock_handle_callback.return_value = mock_google_data
        mock_create_user.return_value = mock_user

        session = self.client.session
        session["oauth_state"] = "test_state"
        session.save()

        response = self.client.get(f"{self.url}?code=test_code&state=test_state")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("success=true", response.url)
        self.assertIn("ext-access", response.cookies)
        self.assertIn("ext-refresh", response.cookies)
        self.assertNotIn("oauth_state", self.client.session)

    def test_post_returns_error_for_missing_code(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "No authorization code received from Google")

    def test_post_returns_error_for_invalid_state(self):
        session = self.client.session
        session["oauth_state"] = "different_state"
        session.save()

        response = self.client.post(self.url, {"code": "test_code", "state": "invalid_state"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Invalid state parameter")

    @patch("todo.services.google_oauth_service.GoogleOAuthService.handle_callback")
    @patch("todo.services.user_service.UserService.create_or_update_user")
    def test_post_handles_callback_successfully(self, mock_create_user, mock_handle_callback):
        mock_google_data = {
            "id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        user_id = str(ObjectId())
        mock_user = Mock()
        mock_user.id = ObjectId(user_id)
        mock_user.google_id = mock_google_data["id"]
        mock_user.email_id = mock_google_data["email"]
        mock_user.name = mock_google_data["name"]
        type(mock_user).id = PropertyMock(return_value=ObjectId(user_id))

        mock_handle_callback.return_value = mock_google_data
        mock_create_user.return_value = mock_user

        session = self.client.session
        session["oauth_state"] = "test_state"
        session.save()

        response = self.client.post(self.url, {"code": "test_code", "state": "test_state"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"]["id"], user_id)
        self.assertEqual(response.data["data"]["user"]["name"], mock_user.name)
        self.assertEqual(response.data["data"]["user"]["email"], mock_user.email_id)
        self.assertEqual(response.data["data"]["user"]["google_id"], mock_user.google_id)
        self.assertIn("ext-access", response.cookies)
        self.assertIn("ext-refresh", response.cookies)
        self.assertNotIn("oauth_state", self.client.session)


class GoogleRefreshViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_refresh")

    def test_get_returns_401_when_no_refresh_token(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], AuthErrorMessages.NO_REFRESH_TOKEN)
        self.assertEqual(response.data["authenticated"], False)
        self.assertEqual(response.data["statusCode"], status.HTTP_401_UNAUTHORIZED)

    @patch("todo.utils.google_jwt_utils.validate_google_refresh_token")
    def test_get_refreshes_token_successfully(self, mock_validate_token):
        user_data = {
            "user_id": str(ObjectId()),
            "google_id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        tokens = generate_google_token_pair(user_data)
        mock_validate_token.return_value = user_data

        self.client.cookies["ext-refresh"] = tokens["refresh_token"]

        response = self.client.get(self.url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["success"], True)
        self.assertEqual(response.data["message"], AppMessages.TOKEN_REFRESHED)
        self.assertIn("ext-access", response.cookies)


class GoogleLogoutViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_logout")

    def test_get_returns_success_and_clears_cookies(self):
        user_data = {
            "user_id": str(ObjectId()),
            "google_id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        tokens = generate_google_token_pair(user_data)
        self.client.cookies["ext-access"] = tokens["access_token"]
        self.client.cookies["ext-refresh"] = tokens["refresh_token"]

        response = self.client.get(self.url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["success"], True)
        self.assertEqual(response.data["message"], AppMessages.GOOGLE_LOGOUT_SUCCESS)
        self.assertEqual(response.cookies.get("ext-access").value, "")
        self.assertEqual(response.cookies.get("ext-refresh").value, "")

    def test_get_redirects_when_not_json_request(self):
        redirect_url = "http://localhost:3000"
        self.client.cookies["ext-access"] = "test_access_token"
        self.client.cookies["ext-refresh"] = "test_refresh_token"

        response = self.client.get(f"{self.url}?redirectURL={redirect_url}")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, redirect_url)
        self.assertEqual(response.cookies.get("ext-access").value, "")
        self.assertEqual(response.cookies.get("ext-refresh").value, "")

    def test_post_returns_success_and_clears_cookies(self):
        user_data = {
            "user_id": str(ObjectId()),
            "google_id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        tokens = generate_google_token_pair(user_data)
        self.client.cookies["ext-access"] = tokens["access_token"]
        self.client.cookies["ext-refresh"] = tokens["refresh_token"]

        response = self.client.post(self.url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["success"], True)
        self.assertEqual(response.data["message"], AppMessages.GOOGLE_LOGOUT_SUCCESS)
        self.assertEqual(response.cookies.get("ext-access").value, "")
        self.assertEqual(response.cookies.get("ext-refresh").value, "")
