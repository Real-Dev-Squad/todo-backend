from typing import Optional, Dict, Any

from todo.constants.permissions import (
    Action,
    ResourceType,
    TaskType,
    get_effective_permissions,
    can_perform_action,
    ROLE_HIERARCHY,
)
from todo.exceptions.permission_exceptions import (
    AccessDeniedError,
    InsufficientPermissionsError,
    TeamMembershipRequiredError,
    ResourceOwnershipRequiredError,
    GlobalModeratorRequiredError,
)
from todo.repositories.role_repository import RoleRepository
from todo.repositories.team_repository import UserTeamDetailsRepository
from todo.repositories.task_repository import TaskRepository


class PermissionService:
    """Service for handling role-based permission checks"""

    @classmethod
    def get_user_team_role(cls, user_id: str, team_id: str) -> Optional[str]:
        """Get user's role in a specific team"""
        user_team = UserTeamDetailsRepository.get_by_user_and_team(user_id, team_id)
        if not user_team or not user_team.is_active:
            return None

        # Get role details from role repository
        role = RoleRepository.get_by_id(user_team.role_id)
        if not role or not role.is_active:
            return None

        return role.name

    @classmethod
    def get_user_global_role(cls, user_id: str) -> Optional[str]:
        """Get user's global role (moderator)"""
        return None

    @classmethod
    def is_team_member(cls, user_id: str, team_id: str) -> bool:
        """Check if user is a member of a team"""
        return cls.get_user_team_role(user_id, team_id) is not None

    @classmethod
    def is_team_owner(cls, user_id: str, team_id: str) -> bool:
        """Check if user is the owner of a team"""
        role = cls.get_user_team_role(user_id, team_id)
        return role == "owner"

    @classmethod
    def is_team_admin_or_owner(cls, user_id: str, team_id: str) -> bool:
        """Check if user is admin or owner of a team"""
        role = cls.get_user_team_role(user_id, team_id)
        return role in ["admin", "owner"]

    @classmethod
    def is_global_moderator(cls, user_id: str) -> bool:
        """Check if user is a global moderator"""
        global_role = cls.get_user_global_role(user_id)
        return global_role == "moderator"

    @classmethod
    def check_team_permission(cls, user_id: str, team_id: str, action: Action) -> bool:
        """Check if user has permission to perform action on team"""
        if cls.is_global_moderator(user_id):
            return can_perform_action("moderator", action, "GLOBAL")

        user_role = cls.get_user_team_role(user_id, team_id)
        if not user_role:
            return False

        return can_perform_action(user_role, action, "TEAM")

    @classmethod
    def check_task_permission(cls, user_id: str, task_id: str, action: Action, task_type: TaskType = None) -> bool:
        """Check if user has permission to perform action on task"""
        task = TaskRepository.get_by_id(task_id)
        if not task:
            return False

        if task.createdBy == user_id:
            return True

        if cls.is_global_moderator(user_id):
            return can_perform_action("moderator", action, "GLOBAL")

        if task_type == TaskType.TEAM:
            return True

        return False

    @classmethod
    def check_role_hierarchy(cls, actor_role: str, target_role: str) -> bool:
        """Check if actor can perform actions on target based on role hierarchy"""
        if actor_role == target_role:
            return False

        if actor_role in ROLE_HIERARCHY:
            return target_role in ROLE_HIERARCHY[actor_role]

        return False

    @classmethod
    def require_team_permission(cls, user_id: str, team_id: str, action: Action) -> None:
        """Require user to have team permission or raise exception"""
        if not cls.check_team_permission(user_id, team_id, action):
            user_role = cls.get_user_team_role(user_id, team_id)
            if not user_role:
                raise TeamMembershipRequiredError(team_id, action.value)
            raise AccessDeniedError(action.value, f"team:{team_id}", user_role)

    @classmethod
    def require_task_permission(cls, user_id: str, task_id: str, action: Action, task_type: TaskType = None) -> None:
        """Require user to have task permission or raise exception"""
        if not cls.check_task_permission(user_id, task_id, action, task_type):
            raise AccessDeniedError(action.value, f"task:{task_id}")

    @classmethod
    def require_global_moderator(cls, user_id: str, action: Action) -> None:
        """Require user to be global moderator or raise exception"""
        if not cls.is_global_moderator(user_id):
            raise GlobalModeratorRequiredError(action.value)

    @classmethod
    def require_team_ownership(cls, user_id: str, team_id: str, action: Action) -> None:
        """Require user to be team owner or raise exception"""
        if not cls.is_team_owner(user_id, team_id):
            raise InsufficientPermissionsError(
                "owner", cls.get_user_team_role(user_id, team_id) or "none", action.value
            )

    @classmethod
    def require_resource_ownership(
        cls, user_id: str, resource_type: ResourceType, resource_id: str, creator_id: str, action: Action
    ) -> None:
        """Require user to be resource owner or raise exception"""
        if user_id != creator_id and not cls.is_global_moderator(user_id):
            raise ResourceOwnershipRequiredError(resource_type.value, resource_id, action.value)

    @classmethod
    def can_add_member_to_team(cls, user_id: str, team_id: str, target_user_id: str) -> bool:
        """Check if user can add a member to team"""
        return cls.check_team_permission(user_id, team_id, Action.ADD_MEMBER)

    @classmethod
    def can_remove_member_from_team(cls, user_id: str, team_id: str, target_user_id: str) -> bool:
        """Check if user can remove a member from team"""
        user_role = cls.get_user_team_role(user_id, team_id)
        target_role = cls.get_user_team_role(target_user_id, team_id)

        if not user_role or not target_role:
            return False

        if not cls.check_team_permission(user_id, team_id, Action.REMOVE_MEMBER):
            return False

        if user_role == "admin" and target_role in ["owner", "admin"]:
            return False

        return True

    @classmethod
    def can_promote_to_admin(cls, user_id: str, team_id: str, target_user_id: str) -> bool:
        """Check if user can promote someone to admin"""
        return cls.is_team_owner(user_id, team_id)

    @classmethod
    def get_user_permissions_summary(cls, user_id: str, team_id: str = None) -> Dict[str, Any]:
        """Get summary of user's permissions"""
        summary = {
            "global_role": cls.get_user_global_role(user_id),
            "is_global_moderator": cls.is_global_moderator(user_id),
            "team_permissions": {},
        }

        if team_id:
            team_role = cls.get_user_team_role(user_id, team_id)
            summary["team_permissions"][team_id] = {
                "role": team_role,
                "permissions": list(get_effective_permissions(team_role or "none", "TEAM")),
            }

        return summary
