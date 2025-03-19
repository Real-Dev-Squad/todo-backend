from unittest import TestCase
from unittest.mock import Mock, patch
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status

from todo.exceptions.exception_handler import handle_exception, format_validation_errors
from todo.dto.responses.error_response import ApiErrorDetail, ApiErrorSource


class ExceptionHandlerTests(TestCase):
    @patch("todo.exceptions.exception_handler.format_validation_errors")
    def test_returns_400_for_validation_error(self, mock_format_validation_errors: Mock):
        validation_error = ValidationError(detail={"field": ["error message"]})
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

    def test_uses_default_handler_for_non_validation_error(self):
        generic_exception = ValueError("Something went wrong")

        response = handle_exception(generic_exception, {})
        self.assertIsNone(response)


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
