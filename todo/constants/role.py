from enum import Enum


class RoleScope(Enum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"


class RoleName(Enum):
    MODERATOR = "moderator"
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


GLOBAL_ROLES = [RoleName.MODERATOR.value]
TEAM_ROLES = [RoleName.OWNER.value, RoleName.ADMIN.value, RoleName.MEMBER.value]

DEFAULT_TEAM_ROLE = RoleName.MEMBER.value

ROLE_SCOPE_CHOICES = [
    (RoleScope.GLOBAL.value, "Global"),
    (RoleScope.TEAM.value, "Team"),
]

VALID_ROLE_NAMES_BY_SCOPE = {
    RoleScope.GLOBAL.value: GLOBAL_ROLES,
    RoleScope.TEAM.value: TEAM_ROLES,
}
