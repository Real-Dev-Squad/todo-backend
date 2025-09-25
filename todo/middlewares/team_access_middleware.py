import logging
from django.http import JsonResponse
from django.urls import resolve
from rest_framework import status

from todo.constants.messages import ApiErrors
from todo.constants.role import RoleScope
from todo.services.user_role_service import UserRoleService

logger = logging.getLogger(__name__)


class TeamAccessMiddleware:
    """
    Middleware to handle team access control for specific routes.
    Only applies to routes that contain 'teams/<team_id>' pattern.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.protected_routes = [
            "team_detail",
            "team_activity_timeline",
        ]

    def __call__(self, request):
        resolved_url = resolve(request.path_info)
        route_name = resolved_url.url_name

        if route_name in self.protected_routes:
            try:
                team_id = resolved_url.kwargs.get("team_id")

                if not team_id:
                    return JsonResponse({"detail": "Team ID is required."}, status=status.HTTP_400_BAD_REQUEST)

                user_id = getattr(request, "user_id", None)

                user_team_roles = UserRoleService.get_user_roles(
                    user_id=user_id, scope=RoleScope.TEAM.value, team_id=team_id
                )

                if not user_team_roles:
                    return JsonResponse({"detail": ApiErrors.UNAUTHORIZED_TITLE}, status=status.HTTP_403_FORBIDDEN)

            except Exception as e:
                logger.error(f"Error in TeamAccessMiddleware: {str(e)}")
                return JsonResponse(
                    {"detail": ApiErrors.INTERNAL_SERVER_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        response = self.get_response(request)
        return response
