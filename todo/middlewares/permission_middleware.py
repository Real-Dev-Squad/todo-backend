import re
from typing import Dict, Optional, Any
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status

from todo.constants.permissions import Action, ResourceType
from todo.services.permission_service import PermissionService
from todo.exceptions.permission_exceptions import (
    PermissionError,
    AccessDeniedError,
    InsufficientPermissionsError,
    TeamMembershipRequiredError,
)
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail


class PermissionMiddleware:
    """Middleware for checking role-based permissions"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.permission_rules = self._setup_permission_rules()

    def __call__(self, request):
        if self._is_public_path(request.path):
            return self.get_response(request)

        if not hasattr(request, "user_id"):
            return self.get_response(request)

        try:
            self._check_permissions(request)

            response = self.get_response(request)
            return response

        except PermissionError as e:
            return self._handle_permission_error(e)
        except Exception as e:
            if settings.DEBUG:
                return self._handle_permission_error(PermissionError(str(e)))
            return self._handle_permission_error(PermissionError("Permission check failed"))

    def _setup_permission_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup permission rules for different endpoints"""
        return {
            r"^/v1/teams/?$": {
                "GET": {"action": Action.VIEW_TEAM, "resource": ResourceType.TEAM},
                "POST": {"action": Action.CREATE_TEAM, "resource": ResourceType.TEAM},
            },
            r"^/v1/teams/(?P<team_id>[^/]+)/?$": {
                "GET": {"action": Action.VIEW_TEAM, "resource": ResourceType.TEAM, "team_check": True},
                "PATCH": {"action": Action.UPDATE_TEAM, "resource": ResourceType.TEAM, "team_check": True},
                "DELETE": {"action": Action.DELETE_TEAM, "resource": ResourceType.TEAM, "owner_only": True},
            },
            r"^/v1/teams/(?P<team_id>[^/]+)/members/?$": {
                "GET": {"action": Action.VIEW_MEMBERS, "resource": ResourceType.TEAM, "team_check": True},
                "POST": {"action": Action.ADD_MEMBER, "resource": ResourceType.TEAM, "admin_or_owner": True},
            },
            r"^/v1/teams/(?P<team_id>[^/]+)/members/(?P<user_id>[^/]+)/?$": {
                "DELETE": {
                    "action": Action.REMOVE_MEMBER,
                    "resource": ResourceType.TEAM,
                    "custom_check": "remove_member",
                }
            },
            r"^/v1/teams/(?P<team_id>[^/]+)/admins/?$": {
                "POST": {"action": Action.ADD_ADMIN, "resource": ResourceType.TEAM, "owner_only": True}
            },
            r"^/v1/tasks/?$": {
                "GET": {"action": Action.VIEW_TASK, "resource": ResourceType.TASK},
                "POST": {"action": Action.CREATE_TASK, "resource": ResourceType.TASK},
            },
            r"^/v1/tasks/(?P<task_id>[^/]+)/?$": {
                "GET": {"action": Action.VIEW_TASK, "resource": ResourceType.TASK, "task_check": True},
                "PATCH": {"action": Action.UPDATE_TASK, "resource": ResourceType.TASK, "task_check": True},
                "DELETE": {"action": Action.DELETE_TASK, "resource": ResourceType.TASK, "task_check": True},
            },
            r"^/v1/roles/?$": {
                "GET": {"action": Action.VIEW_ROLE, "resource": ResourceType.ROLE, "moderator_only": True},
                "POST": {"action": Action.CREATE_ROLE, "resource": ResourceType.ROLE, "moderator_only": True},
            },
            r"^/v1/roles/(?P<role_id>[^/]+)/?$": {
                "GET": {"action": Action.VIEW_ROLE, "resource": ResourceType.ROLE, "moderator_only": True},
                "PATCH": {"action": Action.UPDATE_ROLE, "resource": ResourceType.ROLE, "moderator_only": True},
                "DELETE": {"action": Action.DELETE_ROLE, "resource": ResourceType.ROLE, "moderator_only": True},
            },
        }

    def _check_permissions(self, request):
        """Check permissions for the current request"""
        path = request.path
        method = request.method

        rule = self._find_matching_rule(path, method)
        if not rule:
            return

        params = self._extract_path_params(path, rule["pattern"])

        self._check_rule_permissions(request, rule["config"], params)

    def _find_matching_rule(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        for pattern, methods in self.permission_rules.items():
            if re.match(pattern, path) and method in methods:
                return {"pattern": pattern, "config": methods[method]}
        return None

    def _extract_path_params(self, path: str, pattern: str) -> Dict[str, str]:
        """Extract path parameters from URL"""
        match = re.match(pattern, path)
        if match:
            return match.groupdict()
        return {}

    def _check_rule_permissions(self, request, rule_config: Dict[str, Any], params: Dict[str, str]):
        """Check permissions based on rule configuration"""
        user_id = request.user_id

        if rule_config.get("moderator_only"):
            if not PermissionService.is_global_moderator(user_id):
                raise AccessDeniedError(rule_config["action"].value, rule_config["resource"].value, "non-moderator")
            return

        if rule_config.get("team_check") and "team_id" in params:
            team_id = params["team_id"]

            if rule_config.get("owner_only"):
                if not PermissionService.is_team_owner(user_id, team_id):
                    raise InsufficientPermissionsError(
                        "owner",
                        PermissionService.get_user_team_role(user_id, team_id) or "none",
                        rule_config["action"].value,
                    )
            elif rule_config.get("admin_or_owner"):
                if not PermissionService.is_team_admin_or_owner(user_id, team_id):
                    raise InsufficientPermissionsError(
                        "admin or owner",
                        PermissionService.get_user_team_role(user_id, team_id) or "none",
                        rule_config["action"].value,
                    )
            else:
                if not PermissionService.is_team_member(user_id, team_id):
                    raise TeamMembershipRequiredError(team_id, rule_config["action"].value)

        if rule_config.get("task_check") and "task_id" in params:
            pass

        if rule_config.get("custom_check"):
            self._check_custom_permissions(request, rule_config, params)

    def _check_custom_permissions(self, request, rule_config: Dict[str, Any], params: Dict[str, str]):
        """Handle custom permission checks"""
        custom_check = rule_config["custom_check"]
        user_id = request.user_id

        if custom_check == "remove_member":
            team_id = params.get("team_id")
            target_user_id = params.get("user_id")

            if not team_id or not target_user_id:
                raise AccessDeniedError(rule_config["action"].value, "team", "invalid_params")

            if not PermissionService.can_remove_member_from_team(user_id, team_id, target_user_id):
                raise AccessDeniedError(
                    rule_config["action"].value,
                    f"team:{team_id}",
                    PermissionService.get_user_team_role(user_id, team_id) or "none",
                )

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no authentication required)"""
        public_paths = getattr(settings, "PUBLIC_PATHS", [])
        return any(path.startswith(public_path) for public_path in public_paths)

    def _handle_permission_error(self, error: PermissionError) -> JsonResponse:
        """Handle permission errors and return appropriate response"""
        if isinstance(error, AccessDeniedError):
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_403_FORBIDDEN,
                message=f"Access denied: {error.action} on {error.resource}",
                errors=[ApiErrorDetail(title="Permission Denied", detail=str(error))],
            )
            return JsonResponse(
                data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_403_FORBIDDEN
            )

        elif isinstance(error, InsufficientPermissionsError):
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_403_FORBIDDEN,
                message=f"Insufficient permissions: {error.action}",
                errors=[ApiErrorDetail(title="Insufficient Permissions", detail=str(error))],
            )
            return JsonResponse(
                data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_403_FORBIDDEN
            )

        elif isinstance(error, TeamMembershipRequiredError):
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_403_FORBIDDEN,
                message="Team membership required",
                errors=[ApiErrorDetail(title="Team Membership Required", detail=str(error))],
            )
            return JsonResponse(
                data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_403_FORBIDDEN
            )

        else:
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_403_FORBIDDEN,
                message="Permission denied",
                errors=[ApiErrorDetail(title="Permission Error", detail=str(error))],
            )
            return JsonResponse(
                data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_403_FORBIDDEN
            )
