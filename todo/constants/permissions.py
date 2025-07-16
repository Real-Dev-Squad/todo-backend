from enum import Enum
from typing import Dict, Set


class TeamRole(Enum):
    """Team role hierarchy: Owner > Admin > Member"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class TeamPermission(Enum):
    VIEW_TEAM = "view_team"
    UPDATE_TEAM = "update_team"
    DELETE_TEAM = "delete_team"
    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"
    PROMOTE_TO_ADMIN = "promote_to_admin"
    DEMOTE_ADMIN = "demote_admin"
    VIEW_MEMBERS = "view_members"
    CREATE_TEAM_TASK = "create_team_task"
    VIEW_TEAM_TASKS = "view_team_tasks"


TEAM_ROLE_PERMISSIONS: Dict[TeamRole, Set[TeamPermission]] = {
    TeamRole.OWNER: {
        TeamPermission.VIEW_TEAM,
        TeamPermission.UPDATE_TEAM,
        TeamPermission.DELETE_TEAM,
        TeamPermission.ADD_MEMBER,
        TeamPermission.REMOVE_MEMBER,
        TeamPermission.PROMOTE_TO_ADMIN,
        TeamPermission.DEMOTE_ADMIN,
        TeamPermission.VIEW_MEMBERS,
        TeamPermission.CREATE_TEAM_TASK,
        TeamPermission.VIEW_TEAM_TASKS,
    },
    TeamRole.ADMIN: {
        TeamPermission.VIEW_TEAM,
        TeamPermission.UPDATE_TEAM,
        TeamPermission.ADD_MEMBER,
        TeamPermission.REMOVE_MEMBER,
        TeamPermission.VIEW_MEMBERS,
        TeamPermission.CREATE_TEAM_TASK,
        TeamPermission.VIEW_TEAM_TASKS,
    },
    TeamRole.MEMBER: {
        TeamPermission.VIEW_TEAM,
        TeamPermission.VIEW_MEMBERS,
        TeamPermission.CREATE_TEAM_TASK,
        TeamPermission.VIEW_TEAM_TASKS,
    },
}


def has_team_permission(user_role: TeamRole, permission: TeamPermission) -> bool:
    """Check if role has permission"""
    return permission in TEAM_ROLE_PERMISSIONS.get(user_role, set())


def can_manage_user_in_hierarchy(actor_role: TeamRole, target_role: TeamRole) -> bool:
    """Check if actor can manage target based on hierarchy"""
    if actor_role == TeamRole.OWNER:
        return True
    if actor_role == TeamRole.ADMIN:
        return target_role == TeamRole.MEMBER
    return False
