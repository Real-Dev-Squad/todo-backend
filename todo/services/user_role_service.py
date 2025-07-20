from typing import List, Dict, Any, Optional
import logging

from todo.repositories.user_role_repository import UserRoleRepository
from todo.constants.role import DEFAULT_TEAM_ROLE, ROLE_OWNER, VALID_ROLE_NAMES_BY_SCOPE, RoleScope, RoleName

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
            # Validate role against predefined roles
            if not cls._validate_role(role_name, scope):
                logger.error(f"Invalid role '{role_name}' for scope '{scope}'")
                return False

            # Validate scope requirements
            if scope == "TEAM" and not team_id:
                logger.error("team_id is required for TEAM scope roles")
                return False

            if scope == "GLOBAL" and team_id:
                logger.error("team_id should not be provided for GLOBAL scope roles")
                return False

            # Convert strings to enums for repository
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
            # Convert strings to enums for repository
            role_enum = RoleName(role_name)
            scope_enum = RoleScope(scope)

            return UserRoleRepository.remove_role(user_id, role_enum, scope_enum, team_id)
        except Exception as e:
            logger.error(f"Failed to remove role: {str(e)}")
            return False

    @classmethod
    def get_user_roles(
        cls, user_id: str, scope: Optional[str] = None, team_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            # Convert scope string to enum if provided
            scope_enum = RoleScope(scope) if scope else None

            user_roles = UserRoleRepository.get_user_roles(user_id, scope_enum, team_id)
            return [
                {
                    "role_name": role.role_name.value,  # Convert enum to string for API response
                    "scope": role.scope.value,
                    "team_id": role.team_id,
                    "assigned_at": role.created_at,
                }
                for role in user_roles
            ]
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
        return cls.assign_role(user_id, ROLE_OWNER, "TEAM", team_id)

    @classmethod
    def get_valid_roles_for_scope(cls, scope: str) -> List[str]:
        """Get all valid role names for a given scope."""
        return VALID_ROLE_NAMES_BY_SCOPE.get(scope, [])
