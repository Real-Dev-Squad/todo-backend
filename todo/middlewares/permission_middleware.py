import re
import logging
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status

from todo.services.permission_service import PermissionService
from todo.exceptions.permission_exceptions import PermissionDeniedError
from todo.constants.permissions import TeamPermission

logger = logging.getLogger(__name__)


class PermissionMiddleware:
    """Route-level RBAC middleware for team and task access control"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_public_path(request.path) or not hasattr(request, "user_id"):
            return self.get_response(request)

        try:
            self._check_permissions(request)
            return self.get_response(request)
        except PermissionDeniedError as e:
            return self._error_response(str(e))

    def _check_permissions(self, request):
        """Check permissions based on route patterns"""
        path = request.path
        method = request.method
        user_id = request.user_id

        if team_match := re.match(r"^/v1/teams/([^/]+)/?$", path):
            team_id = team_match.group(1)
            if method == "GET":
                PermissionService.require_team_membership(user_id, team_id, "view team")
            elif method in ["PATCH", "PUT"]:
                PermissionService.require_team_permission(user_id, team_id, TeamPermission.UPDATE_TEAM)
            elif method == "DELETE":
                PermissionService.require_team_owner(user_id, team_id, "delete team")

        elif task_match := re.match(r"^/v1/tasks/([^/]+)/?$", path):
            task_id = task_match.group(1)
            if method == "GET":
                PermissionService.require_task_access(user_id, task_id)
            elif method in ["PATCH", "PUT", "DELETE"]:
                PermissionService.require_task_modify(user_id, task_id)

    def _is_public_path(self, path):
        """Check if path is public"""
        public_paths = getattr(settings, "PUBLIC_PATHS", ["/v1/health", "/v1/auth/"])
        return any(path.startswith(p) for p in public_paths)

    def _error_response(self, message):
        """Return error response"""
        return JsonResponse({"error": "Permission denied", "message": message}, status=status.HTTP_403_FORBIDDEN)
