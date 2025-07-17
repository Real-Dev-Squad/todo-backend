import logging
from typing import Optional, List

from todo.constants.permissions import TeamRole, TeamPermission, has_team_permission, can_manage_user_in_hierarchy
from todo.exceptions.permission_exceptions import (
    TeamPermissionDeniedError,
    TeamMembershipRequiredError,
    InsufficientRoleError,
    TaskAccessDeniedError,
    HierarchyViolationError,
)
from todo.repositories.team_repository import UserTeamDetailsRepository
from todo.repositories.role_repository import RoleRepository
from todo.repositories.task_repository import TaskRepository
from todo.repositories.assignee_task_details_repository import AssigneeTaskDetailsRepository

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for RBAC permissions"""

    @classmethod
    def get_user_team_role(cls, user_id: str, team_id: str) -> Optional[TeamRole]:
        """Get user's role in a team"""
        try:
            user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)

            for user_team in user_teams:
                if str(user_team.team_id) == team_id and user_team.is_active:
                    role = RoleRepository.get_by_id(user_team.role_id)
                    if role and role.is_active:
                        return cls._map_role_name_to_enum(role.name)

            return None
        except Exception as e:
            logger.error(f"Error getting user team role: {e}")
            return None

    @classmethod
    def _map_role_name_to_enum(cls, role_name: str) -> TeamRole:
        """Map role name to enum"""
        role_mapping = {
            "owner": TeamRole.OWNER,
            "admin": TeamRole.ADMIN,
        }
        return role_mapping.get(role_name.lower(), TeamRole.MEMBER)

    @classmethod
    def is_team_member(cls, user_id: str, team_id: str) -> bool:
        """Check if user is team member"""
        return cls.get_user_team_role(user_id, team_id) is not None

    @classmethod
    def is_team_owner(cls, user_id: str, team_id: str) -> bool:
        """Check if user is team owner"""
        return cls.get_user_team_role(user_id, team_id) == TeamRole.OWNER

    @classmethod
    def is_team_admin_or_owner(cls, user_id: str, team_id: str) -> bool:
        """Check if user is admin or owner"""
        role = cls.get_user_team_role(user_id, team_id)
        return role in [TeamRole.ADMIN, TeamRole.OWNER]

    @classmethod
    def check_team_permission(cls, user_id: str, team_id: str, permission: TeamPermission) -> bool:
        """Check if user has permission in team"""
        user_role = cls.get_user_team_role(user_id, team_id)
        if not user_role:
            return False
        return has_team_permission(user_role, permission)

    @classmethod
    def require_team_permission(cls, user_id: str, team_id: str, permission: TeamPermission) -> None:
        """Require team permission or raise exception"""
        if not cls.check_team_permission(user_id, team_id, permission):
            user_role = cls.get_user_team_role(user_id, team_id)

            if not user_role:
                raise TeamMembershipRequiredError(team_id, permission.value)
            else:
                raise TeamPermissionDeniedError(permission.value, team_id, user_role.value)

    @classmethod
    def require_team_membership(cls, user_id: str, team_id: str, action: str = "perform this action") -> None:
        """Require team membership or raise exception"""
        if not cls.is_team_member(user_id, team_id):
            raise TeamMembershipRequiredError(team_id, action)

    @classmethod
    def require_team_owner(cls, user_id: str, team_id: str, action: str) -> None:
        """Require team owner role or raise exception"""
        if not cls.is_team_owner(user_id, team_id):
            current_role = cls.get_user_team_role(user_id, team_id)
            current_role_str = current_role.value if current_role else "none"
            raise InsufficientRoleError("owner", current_role_str, action)

    @classmethod
    def require_team_admin_or_owner(cls, user_id: str, team_id: str, action: str) -> None:
        """Require admin or owner role or raise exception"""
        if not cls.is_team_admin_or_owner(user_id, team_id):
            current_role = cls.get_user_team_role(user_id, team_id)
            current_role_str = current_role.value if current_role else "none"
            raise InsufficientRoleError("admin or owner", current_role_str, action)

    @classmethod
    def can_manage_team_member(cls, user_id: str, team_id: str, target_user_id: str) -> bool:
        """Check if user can manage another team member"""
        actor_role = cls.get_user_team_role(user_id, team_id)
        target_role = cls.get_user_team_role(target_user_id, team_id)

        if not actor_role or not target_role:
            return False

        return can_manage_user_in_hierarchy(actor_role, target_role)

    @classmethod
    def require_manage_team_member(cls, user_id: str, team_id: str, target_user_id: str, action: str) -> None:
        """Require ability to manage team member or raise exception"""
        if not cls.can_manage_team_member(user_id, team_id, target_user_id):
            actor_role = cls.get_user_team_role(user_id, team_id)
            target_role = cls.get_user_team_role(target_user_id, team_id)

            if not actor_role:
                raise TeamMembershipRequiredError(team_id, action)

            if not target_role:
                raise TeamMembershipRequiredError(team_id, f"target user for {action}")

            raise HierarchyViolationError(action, actor_role.value, target_role.value)

    @classmethod
    def can_view_task(cls, user_id: str, task_id: str) -> bool:
        """Check if user can view task"""
        try:
            task = TaskRepository.get_by_id(task_id)
            if not task:
                return False

            if task.createdBy == user_id:
                return True

            if task.private:
                return False

            return cls._has_task_access_through_assignees(user_id, task_id)

        except Exception as e:
            logger.error(f"Error checking task view permission: {e}")
            return False

    @classmethod
    def can_modify_task(cls, user_id: str, task_id: str) -> bool:
        """Check if user can modify task"""
        try:
            task = TaskRepository.get_by_id(task_id)
            if not task:
                return False

            if task.createdBy == user_id:
                return True

            if task.private:
                return False

            return cls._has_task_access_through_assignees(user_id, task_id)

        except Exception as e:
            logger.error(f"Error checking task modify permission: {e}")
            return False

    @classmethod
    def _has_task_access_through_assignees(cls, user_id: str, task_id: str) -> bool:
        """Check task access through assignee relationships"""
        try:
            assignee_relationship = AssigneeTaskDetailsRepository.get_by_task_id(task_id)

            if not assignee_relationship:
                return True

            if assignee_relationship.relation_type == "user":
                return str(assignee_relationship.assignee_id) == user_id

            elif assignee_relationship.relation_type == "team":
                team_id = str(assignee_relationship.assignee_id)
                return cls.is_team_member(user_id, team_id)

            return False

        except Exception as e:
            logger.error(f"Error checking task access through assignees: {e}")
            return False

    @classmethod
    def require_task_access(cls, user_id: str, task_id: str) -> None:
        """Require task access or raise exception"""
        if not cls.can_view_task(user_id, task_id):
            raise TaskAccessDeniedError(task_id, "Task not accessible")

    @classmethod
    def require_task_modify(cls, user_id: str, task_id: str) -> None:
        """Require task modify access or raise exception"""
        if not cls.can_modify_task(user_id, task_id):
            raise TaskAccessDeniedError(task_id, "Cannot modify task")

    @classmethod
    def get_user_accessible_teams(cls, user_id: str) -> List[str]:
        """Get list of team IDs user has access to"""
        try:
            user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)
            return [str(user_team.team_id) for user_team in user_teams if user_team.is_active]
        except Exception as e:
            logger.error(f"Error getting user accessible teams: {e}")
            return []
