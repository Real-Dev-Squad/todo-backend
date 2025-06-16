import requests
import secrets
from urllib.parse import urlencode
from django.conf import settings

from todo.exceptions.google_auth_exceptions import GoogleAPIException, GoogleAuthException
from todo.constants.messages import ApiErrors


class GoogleOAuthService:
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @classmethod
    def get_authorization_url(cls, redirect_url: str = None) -> tuple[str, str]:
        try:
            state = secrets.token_urlsafe(32)

            params = {
                "client_id": settings.GOOGLE_OAUTH["CLIENT_ID"],
                "redirect_uri": settings.GOOGLE_OAUTH["REDIRECT_URI"],
                "response_type": "code",
                "scope": " ".join(settings.GOOGLE_OAUTH["SCOPES"]),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }

            auth_url = f"{cls.GOOGLE_AUTH_URL}?{urlencode(params)}"
            return auth_url, state

        except Exception:
            raise GoogleAuthException(ApiErrors.GOOGLE_AUTH_FAILED)

    @classmethod
    def handle_callback(cls, authorization_code: str) -> dict:
        try:
            tokens = cls._exchange_code_for_tokens(authorization_code)

            user_info = cls._get_user_info(tokens["access_token"])

            return {
                "google_id": user_info["id"],
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info.get("picture"),
            }

        except Exception as e:
            if isinstance(e, GoogleAPIException):
                raise
            raise GoogleAPIException(ApiErrors.GOOGLE_API_ERROR)

    @classmethod
    def _exchange_code_for_tokens(cls, code: str) -> dict:
        """Exchange authorization code for tokens"""
        try:
            data = {
                "client_id": settings.GOOGLE_OAUTH["CLIENT_ID"],
                "client_secret": settings.GOOGLE_OAUTH["CLIENT_SECRET"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_OAUTH["REDIRECT_URI"],
            }

            response = requests.post(cls.GOOGLE_TOKEN_URL, data=data, timeout=30)

            if response.status_code != 200:
                raise GoogleAPIException(ApiErrors.TOKEN_EXCHANGE_FAILED)

            tokens = response.json()

            if "error" in tokens:
                raise GoogleAPIException(ApiErrors.GOOGLE_API_ERROR)

            return tokens

        except requests.exceptions.RequestException:
            raise GoogleAPIException(ApiErrors.GOOGLE_API_ERROR)

    @classmethod
    def _get_user_info(cls, access_token: str) -> dict:
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(cls.GOOGLE_USER_INFO_URL, headers=headers, timeout=30)

            if response.status_code != 200:
                raise GoogleAPIException(ApiErrors.USER_INFO_FETCH_FAILED.format("HTTP error"))

            user_info = response.json()

            required_fields = ["id", "email", "name"]
            missing_fields = [field for field in required_fields if field not in user_info]

            if missing_fields:
                raise GoogleAPIException(ApiErrors.MISSING_USER_INFO_FIELDS.format(", ".join(missing_fields)))

            return user_info

        except requests.exceptions.RequestException:
            raise GoogleAPIException(ApiErrors.GOOGLE_API_ERROR)
