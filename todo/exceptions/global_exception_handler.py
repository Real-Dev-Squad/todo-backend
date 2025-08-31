import logging
from typing import Dict, Any, Callable
from functools import wraps
from rest_framework import status
from rest_framework.response import Response
from django.conf import settings

from todo.exceptions.role_exceptions import (
    RoleNotFoundException,
    RoleOperationException,
)

logger = logging.getLogger(__name__)


def handle_exceptions(func: Callable) -> Callable:
    """
    Decorator for automatic exception handling in views.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RoleNotFoundException as e:
            logger.error(f"RoleNotFoundException: {e}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except RoleOperationException as e:
            logger.error(f"RoleOperationException: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            error_message = str(e) if settings.DEBUG else "Internal server error"
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return wrapper


class GlobalExceptionHandler:
    """
    Class-based exception handler for centralized exception management.
    Similar to Spring's @ControllerAdvice pattern.
    """

    @staticmethod
    def handle_role_not_found(exc: RoleNotFoundException) -> Dict[str, Any]:
        """Handle RoleNotFoundException"""
        logger.error(f"Role not found: {exc}")
        return {"error": str(exc), "status_code": status.HTTP_404_NOT_FOUND}

    @staticmethod
    def handle_role_operation_error(exc: RoleOperationException) -> Dict[str, Any]:
        """Handle RoleOperationException"""
        logger.error(f"Role operation failed: {exc}")
        return {"error": str(exc), "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR}

    @staticmethod
    def handle_validation_error(exc: Exception) -> Dict[str, Any]:
        """Handle validation errors"""
        logger.error(f"Validation error: {exc}")
        return {"error": "Validation failed", "details": str(exc), "status_code": status.HTTP_400_BAD_REQUEST}

    @staticmethod
    def handle_generic_error(exc: Exception) -> Dict[str, Any]:
        """Handle generic exceptions"""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        error_message = str(exc) if settings.DEBUG else "Internal server error"
        return {"error": error_message, "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR}
