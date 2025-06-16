from todo.constants.messages import AuthErrorMessages, ApiErrors, RepositoryErrors


class BaseGoogleException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class GoogleAuthException(BaseGoogleException):
    def __init__(self, message: str = ApiErrors.GOOGLE_AUTH_FAILED):
        super().__init__(message)


class GoogleTokenExpiredError(BaseGoogleException):
    def __init__(self, message: str = AuthErrorMessages.GOOGLE_TOKEN_EXPIRED):
        super().__init__(message)


class GoogleTokenMissingError(BaseGoogleException):
    def __init__(self, message: str = AuthErrorMessages.NO_ACCESS_TOKEN):
        super().__init__(message)


class GoogleTokenInvalidError(BaseGoogleException):
    def __init__(self, message: str = AuthErrorMessages.GOOGLE_TOKEN_INVALID):
        super().__init__(message)


class GoogleRefreshTokenExpiredError(BaseGoogleException):
    def __init__(self, message: str = AuthErrorMessages.GOOGLE_REFRESH_TOKEN_EXPIRED):
        super().__init__(message)


class GoogleAPIException(BaseGoogleException):
    def __init__(self, message: str = ApiErrors.GOOGLE_API_ERROR):
        super().__init__(message)


class GoogleUserNotFoundException(BaseGoogleException):
    def __init__(self, message: str = RepositoryErrors.USER_NOT_FOUND):
        super().__init__(message)
