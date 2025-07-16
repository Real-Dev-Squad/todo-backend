import re
import logging
from django.http import JsonResponse
from rest_framework import status

from todo.services.permission_service import PermissionService
from todo.exceptions.permission_exceptions import PermissionDeniedError
from todo.constants.permissions import TeamPermission

logger = logging.getLogger(__name__)


class PermissionMiddleware:
    """RBAC middleware with route-specific permission checks"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, "user_id"):
            return self._unauthorized_response()

        try:
            self._check_route_permissions(request)
            return self.get_response(request)
        except PermissionDeniedError as e:
            return self._forbidden_response(str(e))

    def _check_route_permissions(self, request):
        """Route-specific permission checks"""
        path = request.path
        method = request.method
        user_id = request.user_id

        if team_id := self._extract_team_id(path):
            self._check_team_permissions(user_id, team_id, method)
            return

        if task_id := self._extract_task_id(path):
            self._check_task_permissions(user_id, task_id, method)
            return

    def _extract_team_id(self, path):
        """Extract team ID from team routes"""
        match = re.match(r"^/v1/teams/([^/]+)/?$", path)
        return match.group(1) if match else None

    def _extract_task_id(self, path):
        """Extract task ID from task routes"""
        match = re.match(r"^/v1/tasks/([^/]+)/?$", path)
        return match.group(1) if match else None

    def _check_team_permissions(self, user_id, team_id, method):
        """Handle team-specific permissions"""
        if method == "GET":
            PermissionService.require_team_membership(user_id, team_id, "view team")
        elif method in ["PATCH", "PUT"]:
            PermissionService.require_team_permission(user_id, team_id, TeamPermission.UPDATE_TEAM)
        elif method == "DELETE":
            PermissionService.require_team_owner(user_id, team_id, "delete team")

    def _check_task_permissions(self, user_id, task_id, method):
        """Handle task-specific permissions"""
        if method == "GET":
            PermissionService.require_task_access(user_id, task_id)
        elif method in ["PATCH", "PUT", "DELETE"]:
            PermissionService.require_task_modify(user_id, task_id)

    def _unauthorized_response(self):
        """Return 401 for missing authentication"""
        return JsonResponse(
            {"error": "Unauthorized", "message": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    def _forbidden_response(self, message):
        """Return 403 for permission denied"""
        return JsonResponse({"error": "Permission denied", "message": message}, status=status.HTTP_403_FORBIDDEN)
