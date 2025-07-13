from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.http import HttpResponseRedirect
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.services.google_oauth_service import GoogleOAuthService
from todo.services.user_service import UserService
from todo.utils.jwt_utils import generate_token_pair
from todo.constants.messages import AppMessages


class GoogleLoginView(APIView):
    @extend_schema(
        operation_id="google_login",
        summary="Initiate Google OAuth login",
        description="Redirects to Google OAuth authorization URL or returns JSON response with auth URL",
        tags=["auth"],
        parameters=[
            OpenApiParameter(
                name="redirectURL",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="URL to redirect after successful authentication",
                required=False,
            ),
            OpenApiParameter(
                name="format",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Response format: 'json' for JSON response, otherwise redirects",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Google OAuth URL generated successfully"),
            302: OpenApiResponse(description="Redirect to Google OAuth URL"),
        },
    )
    def get(self, request: Request):
        redirect_url = request.query_params.get("redirectURL")
        auth_url, state = GoogleOAuthService.get_authorization_url(redirect_url)
        request.session["oauth_state"] = state

        if request.headers.get("Accept") == "application/json" or request.query_params.get("format") == "json":
            return Response(
                {
                    "statusCode": status.HTTP_200_OK,
                    "message": "Google OAuth URL generated successfully",
                    "data": {"authUrl": auth_url, "state": state},
                }
            )

        return HttpResponseRedirect(auth_url)


class GoogleCallbackView(APIView):
    @extend_schema(
        operation_id="google_callback",
        summary="Handle Google OAuth callback",
        description="Processes the OAuth callback from Google and creates/updates user account",
        tags=["auth"],
        parameters=[
            OpenApiParameter(
                name="code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Authorization code from Google",
                required=True,
            ),
            OpenApiParameter(
                name="state",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="State parameter for CSRF protection",
                required=True,
            ),
            OpenApiParameter(
                name="error",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Error from Google OAuth",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="OAuth callback processed successfully"),
            400: OpenApiResponse(description="Bad request - invalid parameters"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        todo_ui_config = settings.SERVICES.get("TODO_UI", {})
        frontend_callback = (
            f"{todo_ui_config.get('URL', '')}/{todo_ui_config.get('REDIRECT_PATH', '')}"
        )

        if error:
            return HttpResponseRedirect(f"{frontend_callback}?error={error}")

        if not code:
            return HttpResponseRedirect(f"{frontend_callback}?error=missing_code")

        if not state:
            return HttpResponseRedirect(f"{frontend_callback}?error=missing_state")

        stored_state = request.session.get("oauth_state")
        if not stored_state or stored_state != state:
            return HttpResponseRedirect(f"{frontend_callback}?error=invalid_state")

        try:
            google_data = GoogleOAuthService.handle_callback(code)
            user = UserService.create_or_update_user(google_data)
            tokens = generate_token_pair(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                }
            )

            response = HttpResponseRedirect(f"{frontend_callback}?success=true")

            self._set_auth_cookies(response, tokens)
            request.session.pop("oauth_state", None)

            return response

        except Exception:
            return HttpResponseRedirect(f"{frontend_callback}?error=auth_failed")

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.COOKIE_SETTINGS.get("COOKIE_SECURE"),
            "httponly": settings.COOKIE_SETTINGS.get("COOKIE_HTTPONLY"),
            "samesite": settings.COOKIE_SETTINGS.get("COOKIE_SAMESITE"),
        }

    def _set_auth_cookies(self, response, tokens):
        config = self._get_cookie_config()
        response.set_cookie(
            settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"),
            tokens["access_token"],
            max_age=tokens["expires_in"],
            **config,
        )
        response.set_cookie(
            settings.COOKIE_SETTINGS.get("REFRESH_COOKIE_NAME"),
            tokens["refresh_token"],
            max_age=settings.JWT_CONFIG.get("REFRESH_TOKEN_LIFETIME"),
            **config,
        )


class LogoutView(APIView):
    @extend_schema(
        operation_id="google_logout_post",
        summary="Logout user (POST)",
        description="Logout the user by clearing authentication cookies (POST method)",
        tags=["auth"],
        responses={
            200: OpenApiResponse(description="Logout successful"),
        },
    )
    def post(self, request: Request):
        return self._handle_logout(request)

    def _handle_logout(self, request: Request):
        request.session.flush()

        response = Response(
            {
                "statusCode": status.HTTP_200_OK,
                "message": AppMessages.GOOGLE_LOGOUT_SUCCESS,
                "data": {"success": True},
            }
        )

        self._clear_auth_cookies(response)
        return response

    def _clear_auth_cookies(self, response):
        delete_config = {
            "path": "/",
            "domain": settings.COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
        }

        response.delete_cookie(
            settings.COOKIE_SETTINGS.get("ACCESS_COOKIE_NAME"), **delete_config
        )
        response.delete_cookie(
            settings.COOKIE_SETTINGS.get("REFRESH_COOKIE_NAME"), **delete_config
        )

        session_delete_config = {
            "path": getattr(settings, "SESSION_COOKIE_PATH", "/"),
            "domain": getattr(settings, "SESSION_COOKIE_DOMAIN"),
        }
        response.delete_cookie("sessionid", **session_delete_config)
