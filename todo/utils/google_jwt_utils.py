import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

from todo.exceptions.google_auth_exceptions import (
    GoogleTokenExpiredError,
    GoogleTokenInvalidError,
    GoogleRefreshTokenExpiredError,
)

from todo.constants.messages import AuthErrorMessages


def generate_google_access_token(user_data: dict) -> str:
    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=settings.GOOGLE_JWT["ACCESS_TOKEN_LIFETIME"])

        payload = {
            "iss": "todo-app-google-auth",
            "exp": int(expiry.timestamp()),
            "iat": int(now.timestamp()),
            "sub": user_data["google_id"],
            "user_id": user_data["user_id"],
            "google_id": user_data["google_id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "token_type": "access",
        }

        token = jwt.encode(
            payload=payload, key=settings.GOOGLE_JWT["PRIVATE_KEY"], algorithm=settings.GOOGLE_JWT["ALGORITHM"]
        )
        return token

    except Exception as e:
        raise GoogleTokenInvalidError(f"Token generation failed: {str(e)}")


def generate_google_refresh_token(user_data: dict) -> str:
    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=settings.GOOGLE_JWT["REFRESH_TOKEN_LIFETIME"])

        payload = {
            "iss": "todo-app-google-auth",
            "exp": int(expiry.timestamp()),
            "iat": int(now.timestamp()),
            "sub": user_data["google_id"],
            "user_id": user_data["user_id"],
            "google_id": user_data["google_id"],
            "email": user_data["email"],
            "token_type": "refresh",
        }
        token = jwt.encode(
            payload=payload, key=settings.GOOGLE_JWT["PRIVATE_KEY"], algorithm=settings.GOOGLE_JWT["ALGORITHM"]
        )

        return token

    except Exception as e:
        raise GoogleTokenInvalidError(f"Refresh token generation failed: {str(e)}")


def validate_google_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            jwt=token, key=settings.GOOGLE_JWT["PUBLIC_KEY"], algorithms=[settings.GOOGLE_JWT["ALGORITHM"]]
        )

        if payload.get("token_type") != "access":
            raise GoogleTokenInvalidError(AuthErrorMessages.GOOGLE_TOKEN_INVALID)

        return payload

    except jwt.ExpiredSignatureError:
        raise GoogleTokenExpiredError()
    except jwt.InvalidTokenError as e:
        raise GoogleTokenInvalidError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise GoogleTokenInvalidError(f"Token validation failed: {str(e)}")


def validate_google_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            jwt=token, key=settings.GOOGLE_JWT["PUBLIC_KEY"], algorithms=[settings.GOOGLE_JWT["ALGORITHM"]]
        )
        if payload.get("token_type") != "refresh":
            raise GoogleTokenInvalidError(AuthErrorMessages.GOOGLE_TOKEN_INVALID)

        return payload

    except jwt.ExpiredSignatureError:
        raise GoogleRefreshTokenExpiredError()
    except jwt.InvalidTokenError as e:
        raise GoogleTokenInvalidError(f"Invalid refresh token: {str(e)}")
    except Exception as e:
        raise GoogleTokenInvalidError(f"Refresh token validation failed: {str(e)}")


def generate_google_token_pair(user_data: dict) -> dict:
    access_token = generate_google_access_token(user_data)
    refresh_token = generate_google_refresh_token(user_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.GOOGLE_JWT["ACCESS_TOKEN_LIFETIME"],
    }
