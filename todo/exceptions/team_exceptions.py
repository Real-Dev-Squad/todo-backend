from todo.constants.messages import ApiErrors

class BaseTeamException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class CannotRemoveOwnerException(BaseTeamException):
    def __init__(self, message = ApiErrors.UNAUTHORIZED_TITLE):
        super().__init__(message)

class NotTeamAdminException(BaseTeamException):
    def __init__(self, message = ApiErrors.UNAUTHORIZED_TITLE):
        super().__init__(message)

class CannotRemoveTeamPOC(BaseTeamException):
    def __init__(self, message = ApiErrors.CANNOT_REMOVE_POC):
        super().__init__(message)