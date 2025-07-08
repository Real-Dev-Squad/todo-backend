class RoleNotFoundException(Exception):
    def __init__(self, role_id: str | None = None):
        if role_id:
            self.message = f"Role with ID {role_id} not found"
        else:
            self.message = "Role not found"
        super().__init__(self.message)


class RoleAlreadyExistsException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class RoleOperationException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
