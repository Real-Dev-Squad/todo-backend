from todo.constants.messages import AuthErrorMessages, ApiErrors, RepositoryErrors


class BaseException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AuthException(BaseException):
    def __init__(self, message: str = ApiErrors.GOOGLE_AUTH_FAILED):
        super().__init__(message)


class TokenExpiredError(BaseException):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_EXPIRED):
        super().__init__(message)


class TokenMissingError(BaseException):
    def __init__(self, message: str = AuthErrorMessages.NO_ACCESS_TOKEN):
        super().__init__(message)


class TokenInvalidError(BaseException):
    def __init__(self, message: str = AuthErrorMessages.TOKEN_INVALID):
        super().__init__(message)


class RefreshTokenExpiredError(BaseException):
    def __init__(self, message: str = AuthErrorMessages.REFRESH_TOKEN_EXPIRED):
        super().__init__(message)


class APIException(BaseException):
    def __init__(self, message: str = ApiErrors.GOOGLE_API_ERROR):
        super().__init__(message)


class UserNotFoundException(BaseException):
    def __init__(self, message: str = RepositoryErrors.USER_NOT_FOUND):
        super().__init__(message)
