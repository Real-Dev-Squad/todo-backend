from todo.constants.messages import AuthErrorMessages


class TokenMissingError(Exception):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_MISSING):
        self.message = message
        super().__init__(self.message)


class TokenExpiredError(Exception):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_EXPIRED):
        self.message = message
        super().__init__(self.message)


class TokenInvalidError(Exception):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_INVALID):
        self.message = message
        super().__init__(self.message)
