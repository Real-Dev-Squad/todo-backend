from todo.constants.messages import AuthErrorMessages, ApiErrors, RepositoryErrors


class BaseAuthException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AuthException(BaseAuthException):
    def __init__(self, message: str = ApiErrors.GOOGLE_AUTH_FAILED):
        super().__init__(message)


class TokenExpiredError(BaseAuthException):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_EXPIRED):
        super().__init__(message)


class TokenMissingError(BaseAuthException):
    def __init__(self, message: str = AuthErrorMessages.NO_ACCESS_TOKEN):
        super().__init__(message)


class TokenInvalidError(BaseAuthException):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_INVALID):
        super().__init__(message)


class RefreshTokenExpiredError(BaseAuthException):
    def __init__(self, message: str = AuthErrorMessages.REFRESH_TOKEN_EXPIRED):
        super().__init__(message)


class APIException(BaseAuthException):
    def __init__(self, message: str = ApiErrors.GOOGLE_API_ERROR):
        super().__init__(message)


class UserNotFoundException(BaseAuthException):
    def __init__(self, message: str = RepositoryErrors.USER_NOT_FOUND):
        super().__init__(message)
