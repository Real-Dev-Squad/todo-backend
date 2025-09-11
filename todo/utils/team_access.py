import logging

from rest_framework.response import Response
from rest_framework import status

from todo.constants.role import RoleScope
from todo.repositories.team_repository import TeamRepository
from todo.services.user_role_service import UserRoleService

logger = logging.getLogger(__name__)


def has_team_access(user_id: str, team_id: str) -> bool:
    try:
        user_team_roles = UserRoleService.get_user_roles(user_id=user_id, scope=RoleScope.TEAM.value, team_id=team_id)

        if user_team_roles:
            return True

        team = TeamRepository.get_by_id(team_id)
        if not team:
            return False
        if team.poc_id == user_id or team.created_by == user_id:
            return True

        return False

    except Exception as e:
        logger.error(f"Error checking team access for user {user_id} and team {team_id}: {str(e)}")
        return False


def team_access_required(func):
    def wrapper(self, request, *args, **kwargs):
        team_id = kwargs.get("team_id")
        if team_id is None and len(args) > 0:
            team_id = args[0]
        if not team_id:
            return Response({"detail": "Team ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not has_team_access(request.user_id, team_id):
            return Response({"detail": "You are not authorized to view this team."}, status=status.HTTP_403_FORBIDDEN)
        return func(self, request, *args, **kwargs)

    return wrapper
