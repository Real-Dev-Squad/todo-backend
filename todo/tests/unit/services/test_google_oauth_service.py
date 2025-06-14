from unittest import TestCase
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode

from todo.services.google_oauth_service import GoogleOAuthService
from todo.exceptions.google_auth_exceptions import GoogleAPIException, GoogleAuthException
from todo.constants.messages import ApiErrors


class GoogleOAuthServiceTests(TestCase):
    def setUp(self) -> None:
        self.mock_settings = {
            "GOOGLE_OAUTH": {
                "CLIENT_ID": "test-client-id",
                "CLIENT_SECRET": "test-client-secret",
                "REDIRECT_URI": "http://localhost:3000/auth/callback",
                "SCOPES": ["email", "profile"]
            }
        }
        self.valid_user_info = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User"
        }
        self.valid_tokens = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token"
        }

    @patch('todo.services.google_oauth_service.settings')
    @patch('todo.services.google_oauth_service.secrets')
    def test_get_authorization_url_success(self, mock_secrets, mock_settings):
        mock_settings.configure_mock(**self.mock_settings)
        mock_secrets.token_urlsafe.return_value = "test-state"

        auth_url, state = GoogleOAuthService.get_authorization_url()

        self.assertEqual(state, "test-state")
        expected_params = {
            "client_id": self.mock_settings["GOOGLE_OAUTH"]["CLIENT_ID"],
            "redirect_uri": self.mock_settings["GOOGLE_OAUTH"]["REDIRECT_URI"],
            "response_type": "code",
            "scope": " ".join(self.mock_settings["GOOGLE_OAUTH"]["SCOPES"]),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        expected_url = f"{GoogleOAuthService.GOOGLE_AUTH_URL}?{urlencode(expected_params)}"
        self.assertEqual(auth_url, expected_url)

    @patch('todo.services.google_oauth_service.settings')
    def test_get_authorization_url_error(self, mock_settings):
        mock_settings.configure_mock(**self.mock_settings)
        mock_settings.GOOGLE_OAUTH = None

        with self.assertRaises(GoogleAuthException) as context:
            GoogleOAuthService.get_authorization_url()
        self.assertIn(ApiErrors.GOOGLE_AUTH_FAILED, str(context.exception))

    @patch('todo.services.google_oauth_service.GoogleOAuthService._exchange_code_for_tokens')
    @patch('todo.services.google_oauth_service.GoogleOAuthService._get_user_info')
    def test_handle_callback_success(self, mock_get_user_info, mock_exchange_tokens):
        mock_exchange_tokens.return_value = self.valid_tokens
        mock_get_user_info.return_value = self.valid_user_info

        result = GoogleOAuthService.handle_callback("test-code")

        self.assertEqual(result["google_id"], self.valid_user_info["id"])
        self.assertEqual(result["email"], self.valid_user_info["email"])
        self.assertEqual(result["name"], self.valid_user_info["name"])
        mock_exchange_tokens.assert_called_once_with("test-code")
        mock_get_user_info.assert_called_once_with(self.valid_tokens["access_token"])

    @patch('todo.services.google_oauth_service.GoogleOAuthService._exchange_code_for_tokens')
    def test_handle_callback_token_error(self, mock_exchange_tokens):
        mock_exchange_tokens.side_effect = GoogleAPIException(ApiErrors.TOKEN_EXCHANGE_FAILED)

        with self.assertRaises(GoogleAPIException) as context:
            GoogleOAuthService.handle_callback("test-code")
        self.assertIn(ApiErrors.TOKEN_EXCHANGE_FAILED, str(context.exception))

    @patch('todo.services.google_oauth_service.requests.post')
    @patch('todo.services.google_oauth_service.settings')
    def test_exchange_code_for_tokens_success(self, mock_settings, mock_post):
        mock_settings.configure_mock(**self.mock_settings)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.valid_tokens
        mock_post.return_value = mock_response

        result = GoogleOAuthService._exchange_code_for_tokens("test-code")

        self.assertEqual(result, self.valid_tokens)
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        self.assertEqual(call_args["data"]["code"], "test-code")
        self.assertEqual(call_args["data"]["client_id"], "test-client-id")
        self.assertEqual(call_args["data"]["client_secret"], "test-client-secret")

    @patch('todo.services.google_oauth_service.requests.post')
    @patch('todo.services.google_oauth_service.settings')
    def test_exchange_code_for_tokens_error_response(self, mock_settings, mock_post):
        mock_settings.configure_mock(**self.mock_settings)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        with self.assertRaises(GoogleAPIException) as context:
            GoogleOAuthService._exchange_code_for_tokens("test-code")
        self.assertIn(ApiErrors.TOKEN_EXCHANGE_FAILED, str(context.exception))

    @patch('todo.services.google_oauth_service.requests.get')
    def test_get_user_info_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.valid_user_info
        mock_get.return_value = mock_response

        result = GoogleOAuthService._get_user_info("test-token")

        self.assertEqual(result, self.valid_user_info)
        mock_get.assert_called_once()
        call_args = mock_get.call_args[1]
        self.assertEqual(call_args["headers"]["Authorization"], "Bearer test-token")

    @patch('todo.services.google_oauth_service.requests.get')
    def test_get_user_info_missing_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123"}
        mock_get.return_value = mock_response

        with self.assertRaises(GoogleAPIException) as context:
            GoogleOAuthService._get_user_info("test-token")
        self.assertIn(ApiErrors.MISSING_USER_INFO_FIELDS.format("email, name"), str(context.exception))

    @patch('todo.services.google_oauth_service.requests.get')
    def test_get_user_info_error_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        with self.assertRaises(GoogleAPIException) as context:
            GoogleOAuthService._get_user_info("test-token")
        self.assertIn(ApiErrors.USER_INFO_FETCH_FAILED.format("HTTP error"), str(context.exception))
