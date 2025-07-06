from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from todo.services.google_oauth_service import GoogleOAuthService
from todo.services.user_service import UserService
from todo.utils.google_jwt_utils import (
    validate_google_refresh_token,
    validate_google_access_token,
    generate_google_access_token,
    generate_google_token_pair,
)

from todo.constants.messages import AuthErrorMessages, AppMessages
from todo.exceptions.google_auth_exceptions import (
    GoogleAuthException,
    GoogleTokenExpiredError,
    GoogleTokenInvalidError,
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
    """
    This class has two implementations:
    1. Current active implementation (temporary) - For testing and development
    2. Commented implementation - For frontend integration (to be used later)

    The temporary implementation processes the OAuth callback directly and shows a success page.
    The frontend implementation will redirect to the frontend and process the callback via POST request.
    """

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
        if "error" in request.query_params:
            error = request.query_params.get("error")
            raise GoogleAuthException(error)

        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code:
            raise GoogleAuthException("No authorization code received from Google")

        stored_state = request.session.get("oauth_state")
        if not stored_state or stored_state != state:
            raise GoogleAuthException("Invalid state parameter")

        return self._handle_callback_directly(code, request)

    def _handle_callback_directly(self, code, request):
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

            wants_json = (
                "application/json" in request.headers.get("Accept", "").lower()
                or request.query_params.get("format") == "json"
            )

            if wants_json:
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
            else:
                response = HttpResponse(f"""
                    <html>
                    <head><title>✅ Login Successful</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h1>✅ Google OAuth Login Successful!</h1>
                        
                        <h2>🧑‍💻 User Info:</h2>
                        <ul>
                            <li><strong>ID:</strong> {user.id}</li>
                            <li><strong>Name:</strong> {user.name}</li>
                            <li><strong>Email:</strong> {user.email_id}</li>
                            <li><strong>Google ID:</strong> {user.google_id}</li>
                        </ul>
                        
                        <h2>🍪 Authentication Cookies Set:</h2>
                        <ul>
                            <li><strong>Access Token:</strong> ext-access (expires in {tokens['expires_in']} seconds)</li>
                            <li><strong>Refresh Token:</strong> ext-refresh (expires in 7 days)</li>
                        </ul>
                        
                        <h2>🧪 Test Other Endpoints:</h2>
                        <ul>
                            <li><a href="/v1/auth/google/status/">Check Auth Status</a></li>
                            <li><a href="/v1/auth/google/refresh/">Refresh Token</a></li>
                            <li><a href="/v1/auth/google/logout/">Logout</a></li>
                        </ul>
                        
                        <p><strong>Google OAuth integration is working perfectly!</strong></p>
                    </body>
                    </html>
                """)

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


# Frontend integration implementation (to be used later)
"""
class GoogleCallbackViewFrontend(APIView):
    def get(self, request: Request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        frontend_callback = f"{settings.FRONTEND_URL}/auth/callback"

        if error:
            return HttpResponseRedirect(f"{frontend_callback}?error={error}")
        elif code and state:
            return HttpResponseRedirect(f"{frontend_callback}?code={code}&state={state}")
        else:
            return HttpResponseRedirect(f"{frontend_callback}?error=missing_parameters")

    def post(self, request: Request):
        code = request.data.get("code")
        state = request.data.get("state")

        if not code:
            formatted_errors = [
                ApiErrorDetail(
                    source={ApiErrorSource.PARAMETER: "code"},
                    title=ApiErrors.VALIDATION_ERROR,
                    detail=ApiErrors.INVALID_AUTH_CODE,
                )
            ]
            error_response = ApiErrorResponse(
                statusCode=400,
                message=ApiErrors.INVALID_AUTH_CODE,
                errors=formatted_errors
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_400_BAD_REQUEST
            )

        stored_state = request.session.get("oauth_state")
        if not stored_state or stored_state != state:
            formatted_errors = [
                ApiErrorDetail(
                    source={ApiErrorSource.PARAMETER: "state"},
                    title=ApiErrors.VALIDATION_ERROR,
                    detail=ApiErrors.INVALID_STATE_PARAMETER,
                )
            ]
            error_response = ApiErrorResponse(
                statusCode=400,
                message=ApiErrors.INVALID_STATE_PARAMETER,
                errors=formatted_errors
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_400_BAD_REQUEST
            )

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

        response = Response({
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
                    "refresh_token_expires_in": settings.GOOGLE_JWT["REFRESH_TOKEN_LIFETIME"]
                }
            }
        })

        self._set_auth_cookies(response, tokens)
        request.session.pop("oauth_state", None)

        return response

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
"""


class GoogleAuthStatusView(APIView):
    @extend_schema(
        operation_id="google_auth_status",
        summary="Check authentication status",
        description="Check if the user is authenticated and return user information",
        tags=["auth"],
        responses={
            200: OpenApiResponse(description="Authentication status retrieved successfully"),
            401: OpenApiResponse(description="Unauthorized - invalid or missing token"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        access_token = request.COOKIES.get("ext-access")

        if not access_token:
            raise GoogleTokenMissingError(AuthErrorMessages.NO_ACCESS_TOKEN)

        try:
            payload = validate_google_access_token(access_token)
            user = UserService.get_user_by_id(payload["user_id"])
        except Exception as e:
            raise GoogleTokenInvalidError(str(e))

        return Response(
            {
                "statusCode": status.HTTP_200_OK,
                "message": "Authentication status retrieved successfully",
                "data": {
                    "authenticated": True,
                    "user": {
                        "id": str(user.id),
                        "email": user.email_id,
                        "name": user.name,
                        "google_id": user.google_id,
                    },
                },
            }
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

        config = self._get_cookie_config()
        response.delete_cookie("ext-access", **config)
        response.delete_cookie("ext-refresh", **config)

        return response

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SECURE", False),
            "httponly": True,
            "samesite": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SAMESITE", "Lax"),
        }
