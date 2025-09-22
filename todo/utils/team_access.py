import logging

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
        return user_id == team.poc_id

    except Exception as e:
        logger.error(f"Error checking team access for user {user_id} and team {team_id}: {str(e)}")
        return False
