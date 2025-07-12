from enum import Enum


class RoleScope(Enum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"


ROLE_SCOPE_CHOICES = [
    (RoleScope.GLOBAL.value, "Global"),
    (RoleScope.TEAM.value, "Team"),
]

GLOBAL_ROLE_NAMES = [
    "moderator",
]

TEAM_ROLE_NAMES = [
    "owner",
    "admin",
]

VALID_ROLE_NAMES_BY_SCOPE = {
    RoleScope.GLOBAL.value: GLOBAL_ROLE_NAMES,
    RoleScope.TEAM.value: TEAM_ROLE_NAMES,
}
