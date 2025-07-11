class RoleNotFoundException(Exception):
    def __init__(self, role_id: str | None = None):
        message = f"Role with ID {role_id} not found" if role_id else "Role not found"
        super().__init__(message)


class RoleAlreadyExistsException(Exception):
    def __init__(self, role_name: str):
        self.role_name = role_name
        self.message = f"Role with name '{role_name}' already exists"
        super().__init__(self.message)


class RoleOperationException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
