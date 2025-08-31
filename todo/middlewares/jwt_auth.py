from django.conf import settings
from rest_framework import status
from django.http import JsonResponse
from todo.utils.jwt_utils import (
    validate_access_token,
    validate_refresh_token,
    generate_access_token,
)
from todo.exceptions.auth_exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    RefreshTokenExpiredError,
    TokenMissingError,
)
from todo.constants.messages import AuthErrorMessages, ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail
from todo.repositories.user_repository import UserRepository


class JWTAuthenticationMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if self._is_public_path(path):
            return self.get_response(request)

        try:
            auth_success = self._try_authentication(request)
            if auth_success:
                response = self.get_response(request)
                return self._process_response(request, response)
            else:
                error_response = ApiErrorResponse(
                    statusCode=status.HTTP_401_UNAUTHORIZED,
                    message=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                    errors=[
                        ApiErrorDetail(
                            title=ApiErrors.AUTHENTICATION_FAILED,
                            detail=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                        )
                    ],
                )
                return JsonResponse(
                    data=error_response.model_dump(mode="json", exclude_none=True),
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except (TokenMissingError, TokenExpiredError, TokenInvalidError) as e:
            return self._handle_auth_error(e)
        except Exception:
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_401_UNAUTHORIZED,
                message=ApiErrors.AUTHENTICATION_FAILED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.AUTHENTICATION_FAILED,
                        detail=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                    )
                ],
            )
            return JsonResponse(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_401_UNAUTHORIZED,
            )

    def _try_authentication(self, request) -> bool:
        try:
            access_token = request.COOKIES.get(settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"))
            if access_token:
                try:
                    payload = validate_access_token(access_token)
                    self._set_user_data(request, payload)
                    return True
                except (TokenExpiredError, TokenInvalidError):
                    pass

            return self._try_refresh(request)

        except (TokenExpiredError, TokenInvalidError) as e:
            raise e
        except Exception:
            return False

    def _try_refresh(self, request) -> bool:
        """Try to refresh access token"""
        try:
            refresh_token = request.COOKIES.get(settings.COOKIE_SETTINGS.get("REFRESH_COOKIE_NAME"))
            if not refresh_token:
                return False
            payload = validate_refresh_token(refresh_token)

            user_data = {
                "user_id": payload["user_id"],
            }

            new_access_token = generate_access_token(user_data)

            self._set_user_data(request, payload)

            request._new_access_token = new_access_token
            request._access_token_expires = settings.JWT_CONFIG["ACCESS_TOKEN_LIFETIME"]

            return True

        except (RefreshTokenExpiredError, TokenInvalidError):
            return False
        except Exception:
            return False

    def _set_user_data(self, request, payload):
        """Set user data on request with database verification"""
        user_id = payload["user_id"]
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise TokenInvalidError(AuthErrorMessages.INVALID_TOKEN)

        request.user_id = user_id
        request.user_email = user.email_id

    def _process_response(self, request, response):
        """Process response and set new cookies if token was refreshed"""
        if hasattr(request, "_new_access_token"):
            config = self._get_cookie_config()
            response.set_cookie(
                settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"),
                request._new_access_token,
                max_age=request._access_token_expires,
                **config,
            )
        return response

    def _get_cookie_config(self):
        """Get cookie configuration"""
        return {
            "path": "/",
            "domain": settings.COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.COOKIE_SETTINGS.get("COOKIE_SECURE"),
            "httponly": True,
            "samesite": settings.COOKIE_SETTINGS.get("COOKIE_SAMESITE"),
        }

    def _is_public_path(self, path: str) -> bool:
        return any(path.startswith(public_path) for public_path in settings.PUBLIC_PATHS)

    def _handle_auth_error(self, exception):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message=str(exception),
            errors=[ApiErrorDetail(title=ApiErrors.AUTHENTICATION_FAILED, detail=str(exception))],
        )
        return JsonResponse(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status.HTTP_401_UNAUTHORIZED,
        )


def get_current_user_info(request) -> dict:
    if not hasattr(request, "user_id"):
        return None

    user_info = {
        "user_id": request.user_id,
        "email": request.user_email,
    }

    return user_info
