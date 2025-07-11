from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from rest_framework.reverse import reverse
from rest_framework import status
from unittest.mock import patch, Mock, PropertyMock
from bson.objectid import ObjectId

from todo.views.auth import GoogleCallbackView
from todo.utils.jwt_utils import generate_token_pair
from todo.constants.messages import AppMessages
from todo.tests.fixtures.user import google_auth_user_payload, users_db_data


class GoogleLoginViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_login")

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_returns_redirect_for_html_request(self, mock_get_auth_url):
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
        self.assertEqual(response.data["statusCode"], status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Google OAuth URL generated successfully")
        self.assertEqual(response.data["data"]["authUrl"], mock_auth_url)
        self.assertEqual(response.data["data"]["state"], mock_state)
        mock_get_auth_url.assert_called_once_with(None)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_returns_json_with_format_parameter(self, mock_get_auth_url):
        """Test that format=json parameter returns JSON response"""
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)

        response = self.client.get(f"{self.url}?format=json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["statusCode"], status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Google OAuth URL generated successfully")
        self.assertEqual(response.data["data"]["authUrl"], mock_auth_url)
        self.assertEqual(response.data["data"]["state"], mock_state)
        mock_get_auth_url.assert_called_once_with(None)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_with_redirect_url_html_request(self, mock_get_auth_url):
        """Test HTML request with redirect URL"""
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)
        redirect_url = "http://localhost:3000/callback"

        response = self.client.get(f"{self.url}?redirectURL={redirect_url}")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, mock_auth_url)
        mock_get_auth_url.assert_called_once_with(redirect_url)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_get_with_redirect_url_json_request(self, mock_get_auth_url):
        """Test JSON request with redirect URL"""
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)
        redirect_url = "http://localhost:3000/callback"

        response = self.client.get(f"{self.url}?redirectURL={redirect_url}", HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["authUrl"], mock_auth_url)
        self.assertEqual(response.data["data"]["state"], mock_state)
        mock_get_auth_url.assert_called_once_with(redirect_url)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.get_authorization_url")
    def test_stores_state_in_session(self, mock_get_auth_url):
        """Test that state is stored in session for both request types"""
        mock_auth_url = "https://accounts.google.com/o/oauth2/auth"
        mock_state = "test_state"
        mock_get_auth_url.return_value = (mock_auth_url, mock_state)

        response = self.client.get(self.url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.session.get("oauth_state"), mock_state)


class GoogleCallbackViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_callback")
        self.factory = APIRequestFactory()
        self.view = GoogleCallbackView.as_view()

        self.test_user_data = users_db_data[0]

    def test_get_redirects_for_oauth_error(self):
        error = "access_denied"
        response = self.client.get(f"{self.url}?error={error}")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=access_denied", response.url)

    def test_get_redirects_for_missing_code(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=missing_code", response.url)

    def test_get_redirects_for_missing_state(self):
        response = self.client.get(f"{self.url}?code=test_code")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=missing_state", response.url)

    def test_get_redirects_for_invalid_state(self):
        session = self.client.session
        session["oauth_state"] = "correct_state"
        session.save()

        response = self.client.get(f"{self.url}?code=test_code&state=wrong_state")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    @patch("todo.services.google_oauth_service.GoogleOAuthService.handle_callback")
    @patch("todo.services.user_service.UserService.create_or_update_user")
    def test_get_redirects_for_valid_code_and_state(self, mock_create_user, mock_handle_callback):
        mock_google_data = {
            "id": self.test_user_data["google_id"],
            "email": self.test_user_data["email_id"],
            "name": self.test_user_data["name"],
        }

        user_id = str(ObjectId())
        mock_user = Mock()
        mock_user.id = ObjectId(user_id)
        mock_user.google_id = self.test_user_data["google_id"]
        mock_user.email_id = self.test_user_data["email_id"]
        mock_user.name = self.test_user_data["name"]
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

    @patch("todo.services.google_oauth_service.GoogleOAuthService.handle_callback")
    def test_get_redirects_for_callback_exception(self, mock_handle_callback):
        mock_handle_callback.side_effect = Exception("OAuth service error")

        session = self.client.session
        session["oauth_state"] = "test_state"
        session.save()

        response = self.client.get(f"{self.url}?code=test_code&state=test_state")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=auth_failed", response.url)


class GoogleLogoutViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse("google_logout")

    def test_get_returns_json_response(self):
        redirect_url = "http://localhost:3000"
        self.client.cookies["ext-access"] = "test_access_token"
        self.client.cookies["ext-refresh"] = "test_refresh_token"

        response = self.client.get(f"{self.url}?redirectURL={redirect_url}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["success"], True)
        self.assertEqual(response.data["message"], AppMessages.GOOGLE_LOGOUT_SUCCESS)
        self.assertEqual(response.cookies.get("ext-access").value, "")
        self.assertEqual(response.cookies.get("ext-refresh").value, "")

    def test_post_returns_success_and_clears_cookies(self):
        """Test that POST requests return JSON"""
        user_data = {
            "user_id": str(ObjectId()),
            "google_id": google_auth_user_payload["google_id"],
            "email": google_auth_user_payload["email"],
            "name": google_auth_user_payload["name"],
        }
        tokens = generate_token_pair(user_data)
        self.client.cookies["ext-access"] = tokens["access_token"]
        self.client.cookies["ext-refresh"] = tokens["refresh_token"]

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["success"], True)
        self.assertEqual(response.data["message"], AppMessages.GOOGLE_LOGOUT_SUCCESS)
        self.assertEqual(response.cookies.get("ext-access").value, "")
        self.assertEqual(response.cookies.get("ext-refresh").value, "")

    def test_logout_clears_session(self):
        """Test that logout clears session data"""
        session = self.client.session
        session["oauth_state"] = "test_state"
        session["some_other_data"] = "test_data"
        session.save()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("oauth_state", self.client.session)
        self.assertNotIn("some_other_data", self.client.session)

    def test_logout_clears_sessionid_cookie(self):
        """Test that logout clears sessionid cookie"""
        self.client.cookies["sessionid"] = "test_session_id"

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies.get("sessionid").value, "")


class UserViewProfileTrueTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("users")
        self.user_data = {
            "user_id": str(ObjectId()),
            "google_id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        tokens = generate_token_pair(self.user_data)
        self.client.cookies["ext-access"] = tokens["access_token"]
        self.client.cookies["ext-refresh"] = tokens["refresh_token"]

    def test_requires_profile_true(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_returns_401_if_not_authenticated(self):
        client = APIClient()
        response = client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, 401)

    def test_returns_user_info(self):
        response = self.client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["user_id"], self.user_data["user_id"])
        self.assertEqual(response.data["data"]["email"], self.user_data["email"])
