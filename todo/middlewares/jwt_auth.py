from django.conf import settings
from rest_framework import status
from django.http import JsonResponse

from todo.utils.jwt_utils import verify_jwt_token
from todo.utils.google_jwt_utils import (
    validate_google_access_token,
    validate_google_refresh_token,
    generate_google_access_token,
)
from todo.exceptions.auth_exceptions import TokenMissingError, TokenExpiredError, TokenInvalidError
from todo.exceptions.google_auth_exceptions import (
    GoogleTokenExpiredError,
    GoogleTokenInvalidError,
    GoogleRefreshTokenExpiredError,
)
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
                    status=status.HTTP_401_UNAUTHORIZED
                )

        except (TokenMissingError, TokenExpiredError, TokenInvalidError) as e:
            return self._handle_rds_auth_error(e)
        except (GoogleTokenExpiredError, GoogleTokenInvalidError) as e:
            return self._handle_google_auth_error(e)
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
                status=status.HTTP_401_UNAUTHORIZED
            )

    def _try_authentication(self, request) -> bool:
        if self._try_google_auth(request):
            return True

        if self._try_rds_auth(request):
            return True

        return False

    def _try_google_auth(self, request) -> bool:
        try:
            google_token = request.COOKIES.get("ext-access")

            if google_token:
                try:
                    payload = validate_google_access_token(google_token)
                    self._set_google_user_data(request, payload)
                    return True
                except (GoogleTokenExpiredError, GoogleTokenInvalidError):
                    pass

            return self._try_google_refresh(request)

        except (GoogleTokenExpiredError, GoogleTokenInvalidError) as e:
            raise e
        except Exception:
            return False

    def _try_google_refresh(self, request) -> bool:
        """Try to refresh Google access token"""
        try:
            refresh_token = request.COOKIES.get("ext-refresh")
            
            if not refresh_token:
                return False
                
            payload = validate_google_refresh_token(refresh_token)
            
            user_data = {
                "user_id": payload["user_id"],
                "google_id": payload["google_id"],
                "email": payload["email"],
                "name": payload.get("name", ""),
            }
            
            new_access_token = generate_google_access_token(user_data)
            
            self._set_google_user_data(request, payload)

            request._new_access_token = new_access_token
            request._access_token_expires = settings.GOOGLE_JWT["ACCESS_TOKEN_LIFETIME"]
            
            return True
            
        except (GoogleRefreshTokenExpiredError, GoogleTokenInvalidError):
            return False
        except Exception:
            return False

    def _set_google_user_data(self, request, payload):
        """Set Google user data on request"""
        request.auth_type = "google"
        request.user_id = payload["user_id"]
        request.google_id = payload["google_id"]
        request.user_email = payload["email"]
        request.user_name = payload.get("name", "")
        request.user_role = "external_user"

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

    def _process_response(self, request, response):
        """Process response and set new cookies if Google token was refreshed"""
        if hasattr(request, '_new_access_token'):
            config = self._get_cookie_config()
            response.set_cookie(
                "ext-access",
                request._new_access_token,
                max_age=request._access_token_expires,
                **config
            )
        return response

    def _get_cookie_config(self):
        """Get Google cookie configuration"""
        return {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SECURE", False),
            "httponly": True,
            "samesite": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SAMESITE", "Lax"),
        }

    def _is_public_path(self, path: str) -> bool:
        return any(path.startswith(public_path) for public_path in settings.PUBLIC_PATHS)

    def _handle_rds_auth_error(self, exception):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message=str(exception),
            errors=[ApiErrorDetail(title=ApiErrors.AUTHENTICATION_FAILED, detail=str(exception))],
        )
        return JsonResponse(
            data=error_response.model_dump(mode="json", exclude_none=True), 
            status=status.HTTP_401_UNAUTHORIZED
        )

    def _handle_google_auth_error(self, exception):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message=str(exception),
            errors=[ApiErrorDetail(title=ApiErrors.AUTHENTICATION_FAILED, detail=str(exception))],
        )
        return JsonResponse(
            data=error_response.model_dump(mode="json", exclude_none=True), 
            status=status.HTTP_401_UNAUTHORIZED
        )


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