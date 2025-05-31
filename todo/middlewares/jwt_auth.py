from django.conf import settings
from todo.auth.jwt_utils import verify_jwt_token
from todo.exceptions.auth_exceptions import TokenMissingError, TokenExpiredError, TokenInvalidError


class JWTAuthenticationMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response
        self.cookie_name = settings.JWT_COOKIE_SETTINGS["RDS_SESSION_V2_COOKIE_NAME"]

    def __call__(self, request):
        path = request.path

        if self._is_public_path(path):
            return self.get_response(request)

        try:
            token = self._extract_token(request)

            if not token:
                raise TokenMissingError()

            payload = verify_jwt_token(token)

            request.user_id = payload["userId"]
            request.user_role = payload["role"]

            return self.get_response(request)

        except (TokenMissingError, TokenExpiredError, TokenInvalidError) as e:
            raise e
        except Exception as e:
            raise TokenInvalidError()

    def _is_public_path(self, path: str) -> bool:
        is_public = any(path.startswith(public_path) for public_path in settings.PUBLIC_PATHS)
        return is_public

    def _extract_token(self, request) -> str | None:
        token = request.COOKIES.get(self.cookie_name)
        return token
