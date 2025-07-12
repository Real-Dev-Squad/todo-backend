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


class RoleAlreadyExistsException(Exception):
    """Exception raised when attempting to create a role that already exists."""

    def __init__(self, role_name: str, existing_role_id: str | None = None):
        message = f"Role with name '{role_name}' already exists"
        if existing_role_id:
            message += f" (ID: {existing_role_id})"

        super().__init__(message)
        self.role_name = role_name
        self.existing_role_id = existing_role_id


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


class RoleValidationException(Exception):
    """Exception raised when role data validation fails."""

    def __init__(self, message: str, field: str | None = None, value: str | None = None):
        if field and value:
            full_message = f"Validation failed for field '{field}' with value '{value}': {message}"
        elif field:
            full_message = f"Validation failed for field '{field}': {message}"
        else:
            full_message = f"Role validation failed: {message}"

        super().__init__(full_message)
        self.field = field
        self.value = value
        self.original_message = message
