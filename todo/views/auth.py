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
from todo.utils.google_jwt_utils import (
    validate_google_refresh_token,
    generate_google_access_token,
    generate_google_token_pair,
)

from todo.constants.messages import AuthErrorMessages, AppMessages
from todo.exceptions.google_auth_exceptions import (
    GoogleAuthException,
    GoogleTokenExpiredError,
    GoogleTokenMissingError,
    GoogleAPIException,
)


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

    @extend_schema(
        operation_id="google_callback_post",
        summary="Handle Google OAuth callback (POST)",
        description="Processes the OAuth callback from Google via POST request",
        tags=["auth"],
        responses={
            200: OpenApiResponse(description="OAuth callback processed successfully"),
            400: OpenApiResponse(description="Bad request - invalid parameters"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        code = request.data.get("code")
        state = request.data.get("state")

        if not code:
            raise GoogleAuthException("No authorization code received from Google")

        stored_state = request.session.get("oauth_state")
        if not stored_state or stored_state != state:
            raise GoogleAuthException("Invalid state parameter")

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

            response = Response(
                {
                    "statusCode": status.HTTP_200_OK,
                    "message": AppMessages.GOOGLE_LOGIN_SUCCESS,
                    "data": {
                        "user": {
                            "id": str(user.id),
                            "name": user.name,
                            "email": user.email_id,
                            "google_id": user.google_id,
                        },
                        "tokens": {
                            "access_token_expires_in": tokens["expires_in"],
                            "refresh_token_expires_in": settings.GOOGLE_JWT["REFRESH_TOKEN_LIFETIME"],
                        },
                    },
                }
            )

            self._set_auth_cookies(response, tokens)
            request.session.pop("oauth_state", None)

            return response
        except Exception as e:
            raise GoogleAPIException(str(e))

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


class GoogleRefreshView(APIView):
    @extend_schema(
        operation_id="google_refresh_token",
        summary="Refresh access token",
        description="Refresh the access token using the refresh token from cookies",
        tags=["auth"],
        responses={
            200: OpenApiResponse(description="Token refreshed successfully"),
            401: OpenApiResponse(description="Unauthorized - invalid or missing refresh token"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        refresh_token = request.COOKIES.get("ext-refresh")

        if not refresh_token:
            raise GoogleTokenMissingError(AuthErrorMessages.NO_REFRESH_TOKEN)

        try:
            payload = validate_google_refresh_token(refresh_token)
            user_data = {
                "user_id": payload["user_id"],
                "google_id": payload["google_id"],
                "email": payload["email"],
                "name": payload.get("name", ""),
            }
            new_access_token = generate_google_access_token(user_data)

            response = Response(
                {"statusCode": status.HTTP_200_OK, "message": AppMessages.TOKEN_REFRESHED, "data": {"success": True}}
            )

            config = self._get_cookie_config()
            response.set_cookie(
                "ext-access", new_access_token, max_age=settings.GOOGLE_JWT["ACCESS_TOKEN_LIFETIME"], **config
            )

            return response
        except Exception as e:
            raise GoogleTokenExpiredError(str(e))

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SECURE", False),
            "httponly": True,
            "samesite": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SAMESITE", "Lax"),
        }


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
        redirect_url = request.query_params.get("redirectURL")

        wants_json = (
            "application/json" in request.headers.get("Accept", "").lower()
            or request.query_params.get("format") == "json"
            or request.method == "POST"
        )

        if wants_json:
            response = Response(
                {
                    "statusCode": status.HTTP_200_OK,
                    "message": AppMessages.GOOGLE_LOGOUT_SUCCESS,
                    "data": {"success": True},
                }
            )
        else:
            redirect_url = redirect_url or "/"
            response = HttpResponseRedirect(redirect_url)

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
        """Clear authentication cookies with only the parameters that delete_cookie accepts"""
        delete_config = {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
        }
        response.delete_cookie("ext-access", **delete_config)
        response.delete_cookie("ext-refresh", **delete_config)
