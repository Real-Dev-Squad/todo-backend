class RoleNotFoundException(Exception):
    """Exception raised when a role is not found."""

    def __init__(self, role_id: str | None = None, role_name: str | None = None):
        if role_id:
            message = f"Role with ID '{role_id}' not found"
        elif role_name:
            message = f"Role with name '{role_name}' not found"
        else:
            message = "Role not found"

        super().__init__(message)
        self.role_id = role_id
        self.role_name = role_name


class RoleOperationException(Exception):
    """Exception raised when a role operation fails."""

    def __init__(self, message: str, operation: str | None = None, role_id: str | None = None):
        if operation and role_id:
            full_message = f"Role operation '{operation}' failed for role ID '{role_id}': {message}"
        elif operation:
            full_message = f"Role operation '{operation}' failed: {message}"
        else:
            full_message = message

        super().__init__(full_message)
        self.operation = operation
        self.role_id = role_id
        self.original_message = message
