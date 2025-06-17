from unittest import TestCase
from unittest.mock import Mock, patch
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.conf import settings

from todo.exceptions.exception_handler import handle_exception, format_validation_errors
from todo.dto.responses.error_response import ApiErrorDetail, ApiErrorSource
from todo.constants.messages import ApiErrors


class ExceptionHandlerTests(TestCase):
    def test_returns_400_for_validation_error(self):
        error_detail = {"field": ["error message"]}
        exception = DRFValidationError(detail=error_detail)
        request = Mock()

        with patch("todo.exceptions.exception_handler.format_validation_errors") as mock_format:
            mock_format.return_value = [
                ApiErrorDetail(detail="error message", source={ApiErrorSource.PARAMETER: "field"})
            ]
            response = handle_exception(exception, {"request": request})

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            expected_response = {
                "statusCode": 400,
                "message": "error message",
                "errors": [{"source": {"parameter": "field"}, "detail": "error message"}],
            }
            self.assertDictEqual(response.data, expected_response)
            mock_format.assert_called_once_with(error_detail)

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
                title=error_message,
            )
            expected_main_message = ApiErrors.INTERNAL_SERVER_ERROR

            self.assertEqual(response.data.get("statusCode"), status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data.get("message"), expected_main_message)
            self.assertIsInstance(response.data.get("errors"), list)

            if response.data.get("errors"):
                self.assertEqual(len(response.data["errors"]), 1)
                actual_error_detail_dict = response.data["errors"][0]
                self.assertEqual(actual_error_detail_dict.get("detail"), expected_detail_obj_in_list.detail)
                self.assertEqual(actual_error_detail_dict.get("title"), expected_detail_obj_in_list.title)


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
