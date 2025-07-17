class PermissionDeniedError(Exception):
    """Base permission error"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class TeamPermissionDeniedError(PermissionDeniedError):
    """Team permission denied"""

    def __init__(self, action: str, team_id: str, user_role: str):
        self.action = action
        self.team_id = team_id
        self.user_role = user_role
        message = f"Permission denied: Cannot {action} on team {team_id}"
        if user_role:
            message += f" with role '{user_role}'"
        super().__init__(message)


class TeamMembershipRequiredError(PermissionDeniedError):
    """Team membership required"""

    def __init__(self, team_id: str, action: str):
        self.team_id = team_id
        self.action = action
        message = f"Team membership required: Must be a member of team '{team_id}' to {action}"
        super().__init__(message)


class InsufficientRoleError(PermissionDeniedError):
    """Insufficient role for action"""

    def __init__(self, required_role: str, current_role: str, action: str):
        self.required_role = required_role
        self.current_role = current_role
        self.action = action
        message = f"Insufficient role: '{action}' requires '{required_role}' role, but user has '{current_role}'"
        super().__init__(message)


class TaskAccessDeniedError(PermissionDeniedError):
    """Task access denied"""

    def __init__(self, task_id: str, reason: str = "insufficient permissions"):
        self.task_id = task_id
        self.reason = reason
        message = f"Access denied to task '{task_id}': {reason}"
        super().__init__(message)


class HierarchyViolationError(PermissionDeniedError):
    """Role hierarchy violation"""

    def __init__(self, action: str, actor_role: str, target_role: str):
        self.action = action
        self.actor_role = actor_role
        self.target_role = target_role
        message = f"Hierarchy violation: '{actor_role}' cannot {action} '{target_role}'"
        super().__init__(message)
