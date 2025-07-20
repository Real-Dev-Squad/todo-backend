from enum import Enum


class RoleScope(Enum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"


class RoleName(Enum):
    MODERATOR = "moderator"
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


ROLE_MODERATOR = "moderator"
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

GLOBAL_ROLES = [ROLE_MODERATOR]
TEAM_ROLES = [ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER]

DEFAULT_TEAM_ROLE = ROLE_MEMBER

ROLE_SCOPE_CHOICES = [
    (RoleScope.GLOBAL.value, "Global"),
    (RoleScope.TEAM.value, "Team"),
]

VALID_ROLE_NAMES_BY_SCOPE = {
    RoleScope.GLOBAL.value: GLOBAL_ROLES,
    RoleScope.TEAM.value: TEAM_ROLES,
}
