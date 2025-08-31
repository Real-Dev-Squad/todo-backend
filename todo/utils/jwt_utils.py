import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

from todo.exceptions.auth_exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    RefreshTokenExpiredError,
)

from todo.constants.messages import AuthErrorMessages


def generate_access_token(user_data: dict) -> str:
    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=settings.JWT_CONFIG.get("ACCESS_TOKEN_LIFETIME"))

        payload = {
            "iss": "todo-app-auth",
            "exp": int(expiry.timestamp()),
            "iat": int(now.timestamp()),
            "sub": user_data["user_id"],
            "user_id": user_data["user_id"],
            "token_type": "access",
        }

        token = jwt.encode(
            payload=payload,
            key=settings.JWT_CONFIG.get("PRIVATE_KEY"),
            algorithm=settings.JWT_CONFIG.get("ALGORITHM"),
        )
        return token

    except Exception as e:
        raise TokenInvalidError(f"Token generation failed: {str(e)}")


def generate_refresh_token(user_data: dict) -> str:
    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=settings.JWT_CONFIG.get("REFRESH_TOKEN_LIFETIME"))

        payload = {
            "iss": "todo-app-auth",
            "exp": int(expiry.timestamp()),
            "iat": int(now.timestamp()),
            "sub": user_data["user_id"],
            "user_id": user_data["user_id"],
            "token_type": "refresh",
        }
        token = jwt.encode(
            payload=payload,
            key=settings.JWT_CONFIG.get("PRIVATE_KEY"),
            algorithm=settings.JWT_CONFIG.get("ALGORITHM"),
        )

        return token

    except Exception as e:
        raise TokenInvalidError(f"Refresh token generation failed: {str(e)}")


def validate_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.JWT_CONFIG.get("PUBLIC_KEY"),
            algorithms=[settings.JWT_CONFIG.get("ALGORITHM")],
        )

        if payload.get("token_type") != "access":
            raise TokenInvalidError(AuthErrorMessages.TOKEN_INVALID)

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise TokenInvalidError(f"Token validation failed: {str(e)}")


def validate_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.JWT_CONFIG.get("PUBLIC_KEY"),
            algorithms=[settings.JWT_CONFIG.get("ALGORITHM")],
        )
        if payload.get("token_type") != "refresh":
            raise TokenInvalidError(AuthErrorMessages.TOKEN_INVALID)

        return payload

    except jwt.ExpiredSignatureError:
        raise RefreshTokenExpiredError()
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid refresh token: {str(e)}")
    except Exception as e:
        raise TokenInvalidError(f"Refresh token validation failed: {str(e)}")


def generate_token_pair(user_data: dict) -> dict:
    access_token = generate_access_token(user_data)
    refresh_token = generate_refresh_token(user_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.JWT_CONFIG.get("ACCESS_TOKEN_LIFETIME"),
    }
