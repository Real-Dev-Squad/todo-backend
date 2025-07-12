from enum import Enum


class RoleScope(Enum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"


ROLE_SCOPE_CHOICES = [
    (RoleScope.GLOBAL.value, "Global"),
    (RoleScope.TEAM.value, "Team"),
]

COMMON_ROLE_NAMES = [
    "admin",
    "moderator",
    "member",
    "viewer",
    "editor",
]
