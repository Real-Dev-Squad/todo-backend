from django.conf import settings
from rest_framework import status
from django.http import JsonResponse

from todo.utils.jwt_utils import verify_jwt_token
from todo.utils.google_jwt_utils import validate_google_access_token
from todo.exceptions.auth_exceptions import TokenMissingError, TokenExpiredError, TokenInvalidError
from todo.exceptions.google_auth_exceptions import GoogleTokenExpiredError, GoogleTokenInvalidError
from todo.constants.messages import AuthErrorMessages, ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail


class JWTAuthenticationMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response
        self.rds_cookie_name = settings.JWT_COOKIE_SETTINGS["RDS_SESSION_V2_COOKIE_NAME"]

    def __call__(self, request):
        path = request.path

        if self._is_public_path(path):
            return self.get_response(request)

        try:
            auth_success = self._try_authentication(request)

            if auth_success:
                return self.get_response(request)
            else:
                error_response = ApiErrorResponse(
                    statusCode=status.HTTP_401_UNAUTHORIZED,
                    message=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                    errors=[ApiErrorDetail(detail=AuthErrorMessages.AUTHENTICATION_REQUIRED, title=AuthErrorMessages.AUTHENTICATION_REQUIRED)],
                )
                return JsonResponse(data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_401_UNAUTHORIZED)

        except (TokenMissingError, TokenExpiredError, TokenInvalidError) as e:
            return self._handle_rds_auth_error(e)
        except (GoogleTokenExpiredError, GoogleTokenInvalidError) as e:
            return self._handle_google_auth_error(e)
        except Exception:
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_401_UNAUTHORIZED,
                message=ApiErrors.AUTHENTICATION_FAILED.format(""),
                errors=[ApiErrorDetail(detail=ApiErrors.AUTHENTICATION_FAILED.format(""), title=AuthErrorMessages.AUTHENTICATION_REQUIRED)],
            )
            return JsonResponse(data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_401_UNAUTHORIZED)

    def _try_authentication(self, request) -> bool:
        if self._try_google_auth(request):
            return True

        if self._try_rds_auth(request):
            return True

        return False

    def _try_google_auth(self, request) -> bool:
        try:
            google_token = request.COOKIES.get("ext-access")

            if not google_token:
                return False

            payload = validate_google_access_token(google_token)

            request.auth_type = "google"
            request.user_id = payload["user_id"]
            request.google_id = payload["google_id"]
            request.user_email = payload["email"]
            request.user_name = payload["name"]
            request.user_role = "external_user"

            return True

        except (GoogleTokenExpiredError, GoogleTokenInvalidError) as e:
            raise e
        except Exception:
            return False

    def _try_rds_auth(self, request) -> bool:
        try:
            rds_token = request.COOKIES.get(self.rds_cookie_name)

            if not rds_token:
                return False

            payload = verify_jwt_token(rds_token)

            request.auth_type = "rds"
            request.user_id = payload["userId"]
            request.user_role = payload["role"]

            return True

        except (TokenMissingError, TokenExpiredError, TokenInvalidError) as e:
            raise e
        except Exception:
            return False

    def _is_public_path(self, path: str) -> bool:
        return any(path.startswith(public_path) for public_path in settings.PUBLIC_PATHS)

    def _handle_rds_auth_error(self, exception):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message=str(exception),
            errors=[ApiErrorDetail(detail=str(exception), title=AuthErrorMessages.AUTHENTICATION_REQUIRED)],
        )
        return JsonResponse(data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_401_UNAUTHORIZED)

    def _handle_google_auth_error(self, exception):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message=str(exception),
            errors=[ApiErrorDetail(detail=str(exception), title=AuthErrorMessages.AUTHENTICATION_REQUIRED)],
        )
        return JsonResponse(data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_401_UNAUTHORIZED)


def is_google_user(request) -> bool:
    return getattr(request, "auth_type", None) == "google"


def is_rds_user(request) -> bool:
    return getattr(request, "auth_type", None) == "rds"


def get_current_user_info(request) -> dict:
    if not hasattr(request, "user_id"):
        return None

    user_info = {
        "user_id": request.user_id,
        "auth_type": getattr(request, "auth_type", "unknown"),
    }

    if is_google_user(request):
        user_info.update(
            {
                "google_id": getattr(request, "google_id", None),
                "email": getattr(request, "user_email", None),
                "name": getattr(request, "user_name", None),
            }
        )

    if is_rds_user(request):
        user_info.update(
            {
                "role": getattr(request, "user_role", None),
            }
        )

    return user_info
