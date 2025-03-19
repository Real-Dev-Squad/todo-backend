from typing import List
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.utils.serializer_helpers import ReturnDict

from todo.dto.responses.error_response import ApiErrorDetail, ApiErrorResponse, ApiErrorSource


def handle_exception(exc, context):
    if isinstance(exc, ValidationError):
        return Response(
            ApiErrorResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid request",
                errors=format_validation_errors(exc.detail),
            ).model_dump(mode="json", exclude_none=True),
            status=status.HTTP_400_BAD_REQUEST,
        )
    return exception_handler(exc, context)


def format_validation_errors(errors) -> List[ApiErrorDetail]:
    formatted_errors = []
    if isinstance(errors, ReturnDict | dict):
        for field, messages in errors.items():
            if isinstance(messages, list):
                for message in messages:
                    formatted_errors.append(ApiErrorDetail(detail=message, source={ApiErrorSource.PARAMETER: field}))
            elif isinstance(messages, dict):
                nested_errors = format_validation_errors(messages)
                formatted_errors.extend(nested_errors)
            else:
                formatted_errors.append(ApiErrorDetail(detail=messages, source={ApiErrorSource.PARAMETER: field}))
    return formatted_errors
