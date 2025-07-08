from enum import Enum


class RoleType(Enum):
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class RoleScope(Enum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"


ROLE_TYPE_CHOICES = [role_type.value for role_type in RoleType]
ROLE_SCOPE_CHOICES = [scope.value for scope in RoleScope]
