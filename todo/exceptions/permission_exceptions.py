class PermissionError(Exception):
    """Base exception for permission-related errors"""

    pass


class AccessDeniedError(PermissionError):
    """Raised when user doesn't have permission to perform an action"""

    def __init__(self, action: str, resource: str, user_role: str = None):
        self.action = action
        self.resource = resource
        self.user_role = user_role

        message = f"Access denied: Cannot perform '{action}' on '{resource}'"
        if user_role:
            message += f" with role '{user_role}'"

        super().__init__(message)


class InsufficientPermissionsError(PermissionError):
    """Raised when user has insufficient permissions for an action"""

    def __init__(self, required_role: str, current_role: str, action: str):
        self.required_role = required_role
        self.current_role = current_role
        self.action = action

        message = f"Insufficient permissions: '{action}' requires '{required_role}' role, but user has '{current_role}'"
        super().__init__(message)


class TeamMembershipRequiredError(PermissionError):
    """Raised when user must be a team member to perform an action"""

    def __init__(self, team_id: str, action: str):
        self.team_id = team_id
        self.action = action

        message = f"Team membership required: Must be a member of team '{team_id}' to perform '{action}'"
        super().__init__(message)


class ResourceOwnershipRequiredError(PermissionError):
    """Raised when user must be the owner of a resource to perform an action"""

    def __init__(self, resource_type: str, resource_id: str, action: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action

        message = f"Resource ownership required: Must be owner of {resource_type} '{resource_id}' to perform '{action}'"
        super().__init__(message)


class RoleHierarchyViolationError(PermissionError):
    """Raised when trying to perform an action that violates role hierarchy"""

    def __init__(self, action: str, target_role: str, actor_role: str):
        self.action = action
        self.target_role = target_role
        self.actor_role = actor_role

        message = f"Role hierarchy violation: '{actor_role}' cannot perform '{action}' on '{target_role}'"
        super().__init__(message)


class GlobalModeratorRequiredError(PermissionError):
    """Raised when action requires global moderator permissions"""

    def __init__(self, action: str):
        self.action = action

        message = f"Global moderator required: Action '{action}' requires global moderator permissions"
        super().__init__(message)
