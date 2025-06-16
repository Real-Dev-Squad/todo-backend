from typing import List
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.utils.serializer_helpers import ReturnDict
from django.conf import settings
from bson.errors import InvalidId as BsonInvalidId

from todo.dto.responses.error_response import ApiErrorDetail, ApiErrorResponse, ApiErrorSource
from todo.constants.messages import ApiErrors, ValidationErrors, AuthErrorMessages
from todo.exceptions.task_exceptions import TaskNotFoundException
from .auth_exceptions import TokenExpiredError, TokenMissingError, TokenInvalidError
from .google_auth_exceptions import (
    GoogleAuthException,
    GoogleTokenExpiredError,
    GoogleTokenInvalidError,
    GoogleRefreshTokenExpiredError,
    GoogleAPIException,
    GoogleUserNotFoundException,
)


def format_validation_errors(errors) -> List[ApiErrorDetail]:
    formatted_errors = []
    if isinstance(errors, ReturnDict | dict):
        for field, messages in errors.items():
            details = messages if isinstance(messages, list) else [messages]
            for message_detail in details:
                if isinstance(message_detail, dict):
                    nested_errors = format_validation_errors(message_detail)
                    formatted_errors.extend(nested_errors)
                else:
                    formatted_errors.append(
                        ApiErrorDetail(detail=str(message_detail), source={ApiErrorSource.PARAMETER: field})
                    )
    elif isinstance(errors, list):
        for message_detail in errors:
            formatted_errors.append(ApiErrorDetail(detail=str(message_detail)))
    return formatted_errors


def handle_exception(exc, context):
    response = drf_exception_handler(exc, context)
    task_id = context.get("kwargs", {}).get("task_id")

    error_list = []
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, TokenExpiredError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.HEADER: "Authorization"},
                title=AuthErrorMessages.TOKEN_EXPIRED_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, TokenMissingError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.HEADER: "Authorization"},
                title=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                detail=str(exc),
            )
        )
    elif isinstance(exc, TokenInvalidError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.HEADER: "Authorization"},
                title=AuthErrorMessages.INVALID_TOKEN_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, GoogleTokenExpiredError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.HEADER: "Authorization"},
                title=AuthErrorMessages.TOKEN_EXPIRED_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, GoogleTokenInvalidError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.HEADER: "Authorization"},
                title=AuthErrorMessages.INVALID_TOKEN_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, GoogleRefreshTokenExpiredError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.HEADER: "Authorization"},
                title=AuthErrorMessages.TOKEN_EXPIRED_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, GoogleAuthException):
        status_code = status.HTTP_400_BAD_REQUEST
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.PARAMETER: "google_auth"},
                title=ApiErrors.GOOGLE_AUTH_FAILED,
                detail=str(exc),
            )
        )
    elif isinstance(exc, GoogleAPIException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.PARAMETER: "google_api"},
                title=ApiErrors.GOOGLE_API_ERROR,
                detail=str(exc),
            )
        )
    elif isinstance(exc, GoogleUserNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.PARAMETER: "user_id"},
                title=ApiErrors.RESOURCE_NOT_FOUND_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, TaskNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.PATH: "task_id"} if task_id else None,
                title=ApiErrors.RESOURCE_NOT_FOUND_TITLE,
                detail=str(exc),
            )
        )
    elif isinstance(exc, BsonInvalidId):
        status_code = status.HTTP_400_BAD_REQUEST
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.PATH: "task_id"} if task_id else None,
                title=ApiErrors.VALIDATION_ERROR,
                detail=ValidationErrors.INVALID_TASK_ID_FORMAT,
            )
        )
    elif (
        isinstance(exc, ValueError)
        and hasattr(exc, "args")
        and exc.args
        and (exc.args[0] == ValidationErrors.INVALID_TASK_ID_FORMAT or exc.args[0] == "Invalid ObjectId format")
    ):
        status_code = status.HTTP_400_BAD_REQUEST
        error_list.append(
            ApiErrorDetail(
                source={ApiErrorSource.PATH: "task_id"} if task_id else None,
                title=ApiErrors.VALIDATION_ERROR,
                detail=ValidationErrors.INVALID_TASK_ID_FORMAT,
            )
        )
    elif (
        isinstance(exc, ValueError) and hasattr(exc, "args") and exc.args and isinstance(exc.args[0], ApiErrorResponse)
    ):
        api_error_response = exc.args[0]
        return Response(
            data=api_error_response.model_dump(mode="json", exclude_none=True), status=api_error_response.statusCode
        )
    elif isinstance(exc, DRFValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
        error_list = format_validation_errors(exc.detail)
        if not error_list and exc.detail:
            error_list.append(ApiErrorDetail(detail=str(exc.detail), title=ApiErrors.VALIDATION_ERROR))

    else:
        if response is not None:
            status_code = response.status_code
            if isinstance(response.data, dict) and "detail" in response.data:
                detail_str = str(response.data["detail"])
                error_list.append(ApiErrorDetail(detail=detail_str, title=detail_str))
            elif isinstance(response.data, list):
                for item_error in response.data:
                    error_list.append(ApiErrorDetail(detail=str(item_error), title=str(exc)))
            else:
                error_list.append(
                    ApiErrorDetail(
                        detail=str(response.data) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR,
                        title=str(exc),
                    )
                )
        else:
            error_list.append(
                ApiErrorDetail(detail=str(exc) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR, title=str(exc))
            )

    if not error_list and not (
        isinstance(exc, ValueError) and hasattr(exc, "args") and exc.args and isinstance(exc.args[0], ApiErrorResponse)
    ):
        default_detail_str = str(exc) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR

        error_list.append(ApiErrorDetail(detail=default_detail_str, title=str(exc)))

    final_response_data = ApiErrorResponse(
        statusCode=status_code,
        message=str(exc) if not error_list else error_list[0].detail,
        errors=error_list,
    )
    return Response(data=final_response_data.model_dump(mode="json", exclude_none=True), status=status_code)
