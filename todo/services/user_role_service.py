from typing import List, Dict, Any, Optional
import logging

from todo.repositories.user_role_repository import UserRoleRepository
from todo.constants.role import DEFAULT_TEAM_ROLE, VALID_ROLE_NAMES_BY_SCOPE, RoleScope, RoleName

logger = logging.getLogger(__name__)


class UserRoleService:
    @classmethod
    def _validate_role(cls, role_name: str, scope: str) -> bool:
        """Validate if role_name is allowed for the given scope."""
        valid_roles = VALID_ROLE_NAMES_BY_SCOPE.get(scope, [])
        return role_name in valid_roles

    @classmethod
    def assign_role(cls, user_id: str, role_name: str, scope: str, team_id: Optional[str] = None) -> bool:
        try:
            if not user_id or not user_id.strip():
                logger.error("user_id is required")
                return False

            if not cls._validate_role(role_name, scope):
                logger.error(f"Invalid role '{role_name}' for scope '{scope}'")
                return False

            if scope == "TEAM" and not team_id:
                logger.error("team_id is required for TEAM scope roles")
                return False

            if scope == "GLOBAL" and team_id:
                logger.error("team_id should not be provided for GLOBAL scope roles")
                return False

            role_enum = RoleName(role_name)
            scope_enum = RoleScope(scope)

            UserRoleRepository.assign_role(user_id, role_enum, scope_enum, team_id)
            return True
        except Exception as e:
            logger.error(f"Failed to assign role: {str(e)}")
            return False

    @classmethod
    def remove_role(cls, user_id: str, role_name: str, scope: str, team_id: Optional[str] = None) -> bool:
        try:
            role_enum = RoleName(role_name)
            scope_enum = RoleScope(scope)

            return UserRoleRepository.remove_role(user_id, role_enum, scope_enum, team_id)
        except Exception as e:
            logger.error(f"Failed to remove role: {str(e)}")
            return False

    @classmethod
    def get_user_roles(
        cls, user_id: Optional[str] = None, scope: Optional[str] = None, team_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            scope_enum = RoleScope(scope) if scope else None

            user_roles = UserRoleRepository.get_user_roles(user_id, scope_enum, team_id)

            result = []
            for role in user_roles:
                role_name_value = role.role_name.value if hasattr(role.role_name, "value") else role.role_name
                scope_value = role.scope.value if hasattr(role.scope, "value") else role.scope

                role_dict = {
                    "role_name": role_name_value,
                    "scope": scope_value,
                    "team_id": role.team_id,
                    "assigned_at": role.created_at,
                }
                result.append(role_dict)

            return result
        except Exception as e:
            logger.error(f"Failed to get user roles: {str(e)}")
            return []

    @classmethod
    def has_role(cls, user_id: str, role_name: str, scope: str, team_id: Optional[str] = None) -> bool:
        try:
            user_roles = cls.get_user_roles(user_id, scope, team_id)
            return any(role["role_name"] == role_name for role in user_roles)
        except Exception:
            return False

    @classmethod
    def assign_default_team_role(cls, user_id: str, team_id: str) -> bool:
        return cls.assign_role(user_id, DEFAULT_TEAM_ROLE, "TEAM", team_id)

    @classmethod
    def assign_team_owner(cls, user_id: str, team_id: str) -> bool:
        return cls.assign_role(user_id, RoleName.OWNER.value, "TEAM", team_id)

    @classmethod
    def get_valid_roles_for_scope(cls, scope: str) -> List[str]:
        """Get all valid role names for a given scope."""
        return VALID_ROLE_NAMES_BY_SCOPE.get(scope, [])

    @classmethod
    def get_team_users_with_roles(cls, team_id: str) -> List[Dict[str, Any]]:
        """Get all users in a team with their roles."""
        try:
            from todo.repositories.user_repository import UserRepository

            user_roles = UserRoleRepository.get_user_roles(user_id=None, scope=RoleScope.TEAM, team_id=team_id)

            users_roles_map = {}
            for role in user_roles:
                user_id = role.user_id
                role_name = role.role_name.value if hasattr(role.role_name, "value") else role.role_name

                if user_id not in users_roles_map:
                    users_roles_map[user_id] = []
                users_roles_map[user_id].append(role_name)

            team_users = []
            for user_id, roles in users_roles_map.items():
                user = UserRepository.get_by_id(user_id)
                if user:
                    team_users.append({"user_id": user_id, "user_name": user.name, "roles": roles})

            return team_users
        except Exception as e:
            logger.error(f"Failed to get team users with roles: {str(e)}")
            return []
