from rest_framework.exceptions import AuthenticationFailed
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
from todo.utils.google_jwt_utils import generate_google_token_pair
from todo.constants.messages import ApiErrors, AppMessages
from todo.middlewares.jwt_auth import get_current_user_info


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

        if error:
            frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"
            return HttpResponseRedirect(f"{frontend_callback}?error={error}")

        if not code:
            frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"
            return HttpResponseRedirect(f"{frontend_callback}?error=missing_code")

        if not state:
            frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"
            return HttpResponseRedirect(f"{frontend_callback}?error=missing_state")

        stored_state = request.session.get("oauth_state")
        if not stored_state or stored_state != state:
            frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"
            return HttpResponseRedirect(f"{frontend_callback}?error=invalid_state")

        try:
            google_data = GoogleOAuthService.handle_callback(code)
            user = UserService.create_or_update_user(google_data)

            tokens = generate_google_token_pair(
                {
                    "user_id": str(user.id),
                    "google_id": user.google_id,
                    "email": user.email_id,
                    "name": user.name,
                }
            )

            frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"
            response = HttpResponseRedirect(f"{frontend_callback}?success=true")

            self._set_auth_cookies(response, tokens)
            request.session.pop("oauth_state", None)

            return response

        except Exception:
            frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"
            return HttpResponseRedirect(f"{frontend_callback}?error=auth_failed")

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SECURE", False),
            "httponly": True,
            "samesite": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SAMESITE", "Lax"),
        }

    def _set_auth_cookies(self, response, tokens):
        config = self._get_cookie_config()
        response.set_cookie("ext-access", tokens["access_token"], max_age=tokens["expires_in"], **config)
        response.set_cookie(
            "ext-refresh", tokens["refresh_token"], max_age=settings.GOOGLE_JWT["REFRESH_TOKEN_LIFETIME"], **config
        )


class GoogleLogoutView(APIView):
    @extend_schema(
        operation_id="google_logout",
        summary="Logout user",
        description="Logout the user by clearing authentication cookies",
        tags=["auth"],
        parameters=[
            OpenApiParameter(
                name="redirectURL",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="URL to redirect after logout",
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
            200: OpenApiResponse(description="Logout successful"),
            302: OpenApiResponse(description="Redirect to specified URL or home page"),
        },
    )
    def get(self, request: Request):
        return self._handle_logout(request)

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

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SECURE", False),
            "httponly": True,
            "samesite": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SAMESITE", "Lax"),
        }

    def _clear_auth_cookies(self, response):
        delete_config = {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
        }
        response.delete_cookie("ext-access", **delete_config)
        response.delete_cookie("ext-refresh", **delete_config)

        session_delete_config = {
            "path": getattr(settings, "SESSION_COOKIE_PATH", "/"),
            "domain": getattr(settings, "SESSION_COOKIE_DOMAIN", None),
        }
        response.delete_cookie("sessionid", **session_delete_config)


class UsersView(APIView):
    def get(self, request: Request):
        profile = request.query_params.get("profile")
        if profile == "true":
            user_info = get_current_user_info(request)
            if not user_info:
                raise AuthenticationFailed(ApiErrors.AUTHENTICATION_FAILED)
            return Response(
                {"statusCode": 200, "message": "Current user details fetched successfully", "data": user_info},
                status=200,
            )
        return Response({"statusCode": 404, "message": "Route does not exist.", "data": None}, status=404)
