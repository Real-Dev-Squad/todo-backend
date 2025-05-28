from todo.dto.responses.error_response import ApiErrorSource
from todo.constants.messages import ApiErrors
from todo.exceptions.task_exceptions import TaskNotFoundException
from rest_framework import status
from unittest import TestCase


class TaskNotFoundExceptionTests(TestCase):
    def test_with_task_id_sets_detail_and_source(self):
        exception = TaskNotFoundException(task_id="12345")

        self.assertEqual(exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(exception.api_error_title, ApiErrors.TASK_NOT_FOUND)
        self.assertEqual(exception.detail,
                         ApiErrors.TASK_ID_NOT_FOUND.format("12345"))
        self.assertEqual(exception.api_error_source, {
                         ApiErrorSource.PARAMETER: "task_id"})
        self.assertEqual(exception.default_code, ApiErrors.TASK_NOT_FOUND)

    def test_with_no_task_id_uses_fallback(self):
        exception = TaskNotFoundException()

        self.assertEqual(exception.detail, ApiErrors.TASK_NOT_FOUND)
        self.assertEqual(exception.api_error_title, ApiErrors.TASK_NOT_FOUND)
        self.assertEqual(exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIsNone(exception.api_error_source)
