from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.http import HttpResponseRedirect
from django.conf import settings

from todo.services.google_oauth_service import GoogleOAuthService
from todo.services.user_service import UserService
from todo.utils.google_jwt_utils import (
    generate_google_token_pair,
    validate_google_refresh_token,
    validate_google_access_token,
    generate_google_access_token,
)
from todo.exceptions.google_auth_exceptions import (
    GoogleAuthException,
    GoogleTokenInvalidError,
    GoogleRefreshTokenExpiredError,
    GoogleAPIException,
    GoogleUserNotFoundException,
)
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.constants.messages import ApiErrors, AuthErrorMessages, AppMessages


class GoogleLoginView(APIView):
    def get(self, request: Request):
        try:
            redirect_url = request.query_params.get("redirectURL")
            auth_url, state = GoogleOAuthService.get_authorization_url(redirect_url)
            request.session["oauth_state"] = state

            if request.headers.get("Accept") == "application/json" or request.query_params.get("format") == "json":
                return Response({"authUrl": auth_url, "state": state})

            return HttpResponseRedirect(auth_url)

        except GoogleAuthException as e:
            error_response = ApiErrorResponse(
                statusCode=400,
                message=str(e),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: "google_auth"},
                        title=ApiErrors.GOOGLE_AUTH_FAILED,
                        detail=str(e),
                    )
                ],
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            error_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.OAUTH_INITIALIZATION_FAILED.format(str(e)),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: "oauth_initialization"},
                        title=ApiErrors.UNEXPECTED_ERROR,
                        detail=ApiErrors.OAUTH_INITIALIZATION_FAILED.format(str(e)),
                    )
                ],
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GoogleCallbackView(APIView):
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
        try:
            code = request.data.get("code")
            state = request.data.get("state")

            if not code:
                error_response = ApiErrorResponse(
                    statusCode=400,
                    message=ApiErrors.INVALID_AUTH_CODE,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: "code"},
                            title=ApiErrors.VALIDATION_ERROR,
                            detail=ApiErrors.INVALID_AUTH_CODE,
                        )
                    ],
                )
                return Response(
                    data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_400_BAD_REQUEST
                )

            stored_state = request.session.get("oauth_state")
            if not stored_state or stored_state != state:
                error_response = ApiErrorResponse(
                    statusCode=400,
                    message=ApiErrors.INVALID_STATE_PARAMETER,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: "state"},
                            title=ApiErrors.VALIDATION_ERROR,
                            detail=ApiErrors.INVALID_STATE_PARAMETER,
                        )
                    ],
                )
                return Response(
                    data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_400_BAD_REQUEST
                )

            google_data = GoogleOAuthService.handle_callback(code)
            user = UserService.create_or_update_user(google_data)

            tokens = generate_google_token_pair(
                {
                    "user_id": str(user.id),
                    "google_id": user.googleId,
                    "email": user.emailId,
                    "name": user.name,
                }
            )

            response = Response(
                {
                    "success": True,
                    "user": {"id": str(user.id), "email": user.emailId, "name": user.name, "googleId": user.googleId},
                }
            )

            self._set_auth_cookies(response, tokens)
            request.session.pop("oauth_state", None)

            return response

        except (GoogleAPIException, GoogleUserNotFoundException) as e:
            error_response = ApiErrorResponse(
                statusCode=500,
                message=str(e),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: "google_auth"},
                        title=ApiErrors.AUTHENTICATION_FAILED,
                        detail=str(e),
                    )
                ],
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            error_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.AUTHENTICATION_FAILED.format(str(e)),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: "authentication"},
                        title=ApiErrors.AUTHENTICATION_FAILED,
                        detail=ApiErrors.AUTHENTICATION_FAILED.format(str(e)),
                    )
                ],
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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


class GoogleAuthStatusView(APIView):
    def get(self, request: Request):
        try:
            access_token = request.COOKIES.get("ext-access")

            if not access_token:
                error_response = ApiErrorResponse(
                    statusCode=401,
                    message=AuthErrorMessages.NO_ACCESS_TOKEN,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.HEADER: "Authorization"},
                            title=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                            detail=AuthErrorMessages.NO_ACCESS_TOKEN,
                        )
                    ],
                )
                return Response(
                    data={"authenticated": False, **error_response.model_dump(mode="json", exclude_none=True)},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            payload = validate_google_access_token(access_token)
            user = UserService.get_user_by_id(payload["user_id"])

            return Response(
                {
                    "authenticated": True,
                    "user": {"id": str(user.id), "email": user.emailId, "name": user.name, "googleId": user.googleId},
                }
            )

        except (GoogleTokenInvalidError, GoogleUserNotFoundException) as e:
            error_response = ApiErrorResponse(
                statusCode=401,
                message=str(e),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.HEADER: "Authorization"},
                        title=AuthErrorMessages.INVALID_TOKEN_TITLE,
                        detail=str(e),
                    )
                ],
            )
            return Response(
                data={"authenticated": False, **error_response.model_dump(mode="json", exclude_none=True)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except Exception:
            error_response = ApiErrorResponse(
                statusCode=401,
                message=AuthErrorMessages.TOKEN_INVALID,
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.HEADER: "Authorization"},
                        title=AuthErrorMessages.INVALID_TOKEN_TITLE,
                        detail=AuthErrorMessages.TOKEN_INVALID,
                    )
                ],
            )
            return Response(
                data={"authenticated": False, **error_response.model_dump(mode="json", exclude_none=True)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class GoogleRefreshView(APIView):
    def get(self, request: Request):
        try:
            redirect_url = request.query_params.get("redirectURL")
            refresh_token = request.COOKIES.get("ext-refresh")

            if not refresh_token:
                return self._handle_missing_token(redirect_url)

            payload = validate_google_refresh_token(refresh_token)

            user_data = {
                "user_id": payload["user_id"],
                "google_id": payload["google_id"],
                "email": payload["email"],
                "name": payload.get("name", ""),
            }
            new_access_token = generate_google_access_token(user_data)

            response = Response({"success": True, "message": AppMessages.TOKEN_REFRESHED})

            config = self._get_cookie_config()
            response.set_cookie(
                "ext-access", new_access_token, max_age=settings.GOOGLE_JWT["ACCESS_TOKEN_LIFETIME"], **config
            )

            return response

        except (GoogleTokenInvalidError, GoogleRefreshTokenExpiredError):
            return self._handle_expired_token(redirect_url)
        except Exception as e:
            error_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.TOKEN_REFRESH_FAILED.format(str(e)),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.HEADER: "Authorization"},
                        title=ApiErrors.TOKEN_REFRESH_FAILED,
                        detail=ApiErrors.TOKEN_REFRESH_FAILED.format(str(e)),
                    )
                ],
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "secure": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SECURE", False),
            "httponly": True,
            "samesite": settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_SAMESITE", "Lax"),
        }

    def _handle_missing_token(self, redirect_url):
        error_response = ApiErrorResponse(
            statusCode=401,
            message=AuthErrorMessages.NO_REFRESH_TOKEN,
            errors=[
                ApiErrorDetail(
                    source={ApiErrorSource.HEADER: "Authorization"},
                    title=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                    detail=AuthErrorMessages.NO_REFRESH_TOKEN,
                )
            ],
        )

        response_data = {"requiresLogin": True, **error_response.model_dump(mode="json", exclude_none=True)}

        if redirect_url:
            response_data["redirectUrl"] = redirect_url

        response = Response(data=response_data, status=status.HTTP_401_UNAUTHORIZED)
        self._clear_auth_cookies(response)
        return response

    def _handle_expired_token(self, redirect_url, error_detail):
        error_response = ApiErrorResponse(
            statusCode=401,
            message=AuthErrorMessages.GOOGLE_REFRESH_TOKEN_EXPIRED,
            errors=[
                ApiErrorDetail(
                    source={ApiErrorSource.HEADER: "Authorization"},
                    title=AuthErrorMessages.TOKEN_EXPIRED_TITLE,
                    detail=error_detail,
                )
            ],
        )

        response_data = {"requiresLogin": True, **error_response.model_dump(mode="json", exclude_none=True)}

        if redirect_url:
            response_data["redirectUrl"] = redirect_url

        response = Response(data=response_data, status=status.HTTP_401_UNAUTHORIZED)
        self._clear_auth_cookies(response)
        return response

    def _clear_auth_cookies(self, response):
        domain = settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN")
        response.delete_cookie("ext-access", domain=domain)
        response.delete_cookie("ext-refresh", domain=domain)


class GoogleLogoutView(APIView):
    def get(self, request: Request):
        return self._handle_logout(request)

    def post(self, request: Request):
        return self._handle_logout(request)

    def _handle_logout(self, request: Request):
        try:
            redirect_url = request.query_params.get("redirectURL")

            wants_json = (
                request.headers.get("Accept") == "application/json"
                or request.data.get("format") == "json"
                or request.method == "POST"
            )

            if wants_json:
                response = Response({"success": True, "message": AppMessages.GOOGLE_LOGOUT_SUCCESS})
            else:
                redirect_url = redirect_url or "/"
                response = HttpResponseRedirect(redirect_url)

            domain = settings.GOOGLE_COOKIE_SETTINGS.get("COOKIE_DOMAIN")
            response.delete_cookie("ext-access", domain=domain)
            response.delete_cookie("ext-refresh", domain=domain)

            return response

        except Exception as e:
            error_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.LOGOUT_FAILED.format(str(e)),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: "logout"},
                        title=ApiErrors.LOGOUT_FAILED,
                        detail=ApiErrors.LOGOUT_FAILED.format(str(e)),
                    )
                ],
            )
            return Response(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
