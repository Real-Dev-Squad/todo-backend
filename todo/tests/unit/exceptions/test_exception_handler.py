from unittest import TestCase
from unittest.mock import Mock, patch
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.conf import settings

from todo.exceptions.exception_handler import handle_exception, format_validation_errors
from todo.dto.responses.error_response import ApiErrorDetail, ApiErrorSource
from todo.constants.messages import ApiErrors, ValidationErrors
from todo.exceptions.task_exceptions import TaskStateConflictException, UnprocessableEntityException
from bson.errors import InvalidId as BsonInvalidId


class ExceptionHandlerTests(TestCase):
    @patch("todo.exceptions.exception_handler.format_validation_errors")
    def test_returns_400_for_validation_error(self, mock_format_validation_errors: Mock):
        validation_error = DRFValidationError(detail={"field": ["error message"]})
        mock_format_validation_errors.return_value = [
            ApiErrorDetail(detail="error message", source={ApiErrorSource.PARAMETER: "field"})
        ]

        response = handle_exception(validation_error, {})

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        expected_response = {
            "statusCode": 400,
            "message": "Invalid request",
            "errors": [{"source": {"parameter": "field"}, "detail": "error message"}],
        }
        self.assertDictEqual(response.data, expected_response)

        mock_format_validation_errors.assert_called_once_with(validation_error.detail)

    def test_handles_task_state_conflict_exception(self):
        task_id = "some_task_id"
        exception = TaskStateConflictException(ValidationErrors.CANNOT_DEFER_A_DONE_TASK)
        context = {"kwargs": {"task_id": task_id}}

        response = handle_exception(exception, context)

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["statusCode"], status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["message"], ValidationErrors.CANNOT_DEFER_A_DONE_TASK)
        self.assertEqual(len(response.data["errors"]), 1)
        self.assertEqual(response.data["errors"][0]["title"], ApiErrors.STATE_CONFLICT_TITLE)
        self.assertEqual(response.data["errors"][0]["source"], {"path": "task_id"})

    def test_handles_unprocessable_entity_exception(self):
        exception = UnprocessableEntityException("Cannot process this")
        context = {}
        response = handle_exception(exception, context)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["message"], "Cannot process this")
        self.assertEqual(response.data["errors"][0]["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(response.data["errors"][0]["source"], {"parameter": "deferredTill"})

    def test_handles_bson_invalid_id_exception(self):
        task_id = "invalid-id"
        exception = BsonInvalidId("Invalid ID")
        context = {"kwargs": {"task_id": task_id}}
        response = handle_exception(exception, context)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(response.data["errors"][0]["title"], ApiErrors.VALIDATION_ERROR)
        self.assertEqual(response.data["errors"][0]["detail"], ValidationErrors.INVALID_TASK_ID_FORMAT)
        self.assertEqual(response.data["errors"][0]["source"], {"path": "task_id"})

    def test_custom_handler_formats_generic_exception(self):
        request = None
        context = {"request": request, "view": APIView()}
        error_message = "A truly generic error occurred"
        exception = Exception(error_message)

        with patch("todo.exceptions.exception_handler.drf_exception_handler") as mock_drf_handler:
            mock_drf_handler.return_value = None

            response = handle_exception(exception, context)

            self.assertIsNotNone(response)
            self.assertIsInstance(response, Response)
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

            self.assertIsInstance(response.data, dict)

            expected_detail_obj_in_list = ApiErrorDetail(
                detail=error_message if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR,
                title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
            )
            expected_main_message = ApiErrors.UNEXPECTED_ERROR_OCCURRED

            self.assertEqual(response.data.get("statusCode"), status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data.get("message"), expected_main_message)
            self.assertIsInstance(response.data.get("errors"), list)

            if response.data.get("errors"):
                self.assertEqual(len(response.data["errors"]), 1)
                actual_error_detail_dict = response.data["errors"][0]
                self.assertEqual(actual_error_detail_dict.get("detail"), expected_detail_obj_in_list.detail)
                self.assertEqual(actual_error_detail_dict.get("title"), expected_detail_obj_in_list.title)


class CustomExceptionsTests(TestCase):
    def test_task_state_conflict_exception(self):
        message = "Test conflict message"
        exception = TaskStateConflictException(message)
        self.assertEqual(str(exception), message)


class FormatValidationErrorsTests(TestCase):
    def test_formats_flat_validation_errors(self):
        errors = {"field": ["error message 1", "error message 2"]}
        expected_result = [
            ApiErrorDetail(detail="error message 1", source={ApiErrorSource.PARAMETER: "field"}),
            ApiErrorDetail(detail="error message 2", source={ApiErrorSource.PARAMETER: "field"}),
        ]

        result = format_validation_errors(errors)

        self.assertEqual(result, expected_result)

    def test_formats_nested_validation_errors(self):
        errors = {
            "parent_field": {
                "child_field": ["child error message"],
                "another_child": {"deep_field": ["deep error message"]},
            }
        }
        expected_result = [
            ApiErrorDetail(detail="child error message", source={ApiErrorSource.PARAMETER: "child_field"}),
            ApiErrorDetail(detail="deep error message", source={ApiErrorSource.PARAMETER: "deep_field"}),
        ]

        result = format_validation_errors(errors)

        self.assertEqual(result, expected_result)

    def test_formats_non_list_dict_validation_error(self):
        errors = {"field": "Not a list or dict"}
        expected_result = [ApiErrorDetail(detail="Not a list or dict", source={ApiErrorSource.PARAMETER: "field"})]

        result = format_validation_errors(errors)

        self.assertEqual(result, expected_result)
