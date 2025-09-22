import logging
from django.http import JsonResponse
from django.urls import resolve
from rest_framework import status

from todo.utils.team_access import has_team_access

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
            "add_team_members",
            "team_invite_code",
            "team_activity_timeline",
            "remove_team_member",
            "team_user_roles",
            "team_user_role_detail",
            "team_user_role_delete",
        ]

    def __call__(self, request):
        try:
            resolved_url = resolve(request.path_info)
            route_name = resolved_url.url_name

            if route_name in self.protected_routes:
                team_id = resolved_url.kwargs.get("team_id")

                if not team_id:
                    return JsonResponse({"detail": "Team ID is required."}, status=status.HTTP_400_BAD_REQUEST)

                if not has_team_access(request.user_id, team_id):
                    return JsonResponse(
                        {"detail": "You are not authorized to view this team."}, status=status.HTTP_403_FORBIDDEN
                    )

        except Exception as e:
            logger.error(f"Error in TeamAccessMiddleware: {str(e)}")
            pass

        response = self.get_response(request)
        return response

    # Access logic resides in `todo.utils.team_access.has_team_access`
