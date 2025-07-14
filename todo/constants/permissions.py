from enum import Enum
from typing import Dict, List, Set


class Action(Enum):
    """Actions that can be performed on resources"""

    CREATE_TEAM = "create_team"
    VIEW_TEAM = "view_team"
    UPDATE_TEAM = "update_team"
    DELETE_TEAM = "delete_team"

    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"
    ADD_ADMIN = "add_admin"
    REMOVE_ADMIN = "remove_admin"
    VIEW_MEMBERS = "view_members"

    CREATE_TASK = "create_task"
    VIEW_TASK = "view_task"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    ASSIGN_TASK = "assign_task"

    CREATE_ROLE = "create_role"
    VIEW_ROLE = "view_role"
    UPDATE_ROLE = "update_role"
    DELETE_ROLE = "delete_role"


class ResourceType(Enum):
    TEAM = "team"
    TASK = "task"
    USER = "user"
    ROLE = "role"


class TaskType(Enum):
    """Types of tasks"""

    PRIVATE = "private"
    TEAM = "team"


# Global role permissions (for moderators)
GLOBAL_ROLE_PERMISSIONS: Dict[str, Set[Action]] = {
    "moderator": {
        Action.CREATE_ROLE,
        Action.VIEW_ROLE,
        Action.UPDATE_ROLE,
        Action.DELETE_ROLE,
        Action.VIEW_TEAM,
        Action.VIEW_TASK,
        Action.UPDATE_TASK,
        Action.DELETE_TASK,
    }
}

TEAM_ROLE_PERMISSIONS: Dict[str, Set[Action]] = {
    "owner": {
        Action.VIEW_TEAM,
        Action.UPDATE_TEAM,
        Action.DELETE_TEAM,
        Action.ADD_MEMBER,
        Action.REMOVE_MEMBER,
        Action.ADD_ADMIN,
        Action.REMOVE_ADMIN,
        Action.VIEW_MEMBERS,
        Action.CREATE_TASK,
        Action.VIEW_TASK,
        Action.UPDATE_TASK,
        Action.DELETE_TASK,
        Action.ASSIGN_TASK,
    },
    "admin": {
        Action.VIEW_TEAM,
        Action.UPDATE_TEAM,
        Action.ADD_MEMBER,
        Action.REMOVE_MEMBER,
        Action.VIEW_MEMBERS,
        Action.CREATE_TASK,
        Action.VIEW_TASK,
        Action.UPDATE_TASK,
        Action.DELETE_TASK,
        Action.ASSIGN_TASK,
    },
    # Default member permissions (implicit - all team members have these)
    "member": {
        Action.VIEW_TEAM,
        Action.VIEW_MEMBERS,
        Action.CREATE_TASK,
        Action.VIEW_TASK,
        Action.UPDATE_TASK,  # Only their own tasks
    },
}

ROLE_HIERARCHY: Dict[str, List[str]] = {"owner": ["admin", "member"], "admin": ["member"], "member": []}


def get_effective_permissions(role_name: str, scope: str = "TEAM") -> Set[Action]:
    """Get effective permissions for a role including inherited permissions"""
    if scope == "GLOBAL":
        return GLOBAL_ROLE_PERMISSIONS.get(role_name, set())

    permissions = set()

    if role_name in TEAM_ROLE_PERMISSIONS:
        permissions.update(TEAM_ROLE_PERMISSIONS[role_name])

    if role_name in ROLE_HIERARCHY:
        for inherited_role in ROLE_HIERARCHY[role_name]:
            permissions.update(TEAM_ROLE_PERMISSIONS.get(inherited_role, set()))

    return permissions


def can_perform_action(user_role: str, action: Action, scope: str = "TEAM") -> bool:
    """Check if a user role can perform a specific action"""
    effective_permissions = get_effective_permissions(user_role, scope)
    return action in effective_permissions


TASK_VISIBILITY_RULES = {
    TaskType.PRIVATE: {
        "creator": True,
        "team_member": False,
        "moderator": True,
    },
    TaskType.TEAM: {
        "creator": True,
        "team_member": True,
        "moderator": True,
    },
}
