from todo.constants.messages import AuthErrorMessages, ApiErrors, RepositoryErrors


class GoogleAuthException(Exception):
    def __init__(self, message: str = ApiErrors.GOOGLE_AUTH_FAILED):
        self.message = message
        super().__init__(self.message)


class GoogleTokenExpiredError(Exception):
    def __init__(self, message: str = AuthErrorMessages.GOOGLE_TOKEN_EXPIRED):
        self.message = message
        super().__init__(self.message)


class GoogleTokenInvalidError(Exception):
    def __init__(self, message: str = AuthErrorMessages.GOOGLE_TOKEN_INVALID):
        self.message = message
        super().__init__(self.message)


class GoogleRefreshTokenExpiredError(Exception):
    def __init__(self, message: str = AuthErrorMessages.GOOGLE_REFRESH_TOKEN_EXPIRED):
        self.message = message
        super().__init__(self.message)


class GoogleAPIException(Exception):
    def __init__(self, message: str = ApiErrors.GOOGLE_API_ERROR):
        self.message = message
        super().__init__(self.message)


class GoogleUserNotFoundException(Exception):
    def __init__(self, message: str = RepositoryErrors.USER_NOT_FOUND):
        self.message = message
        super().__init__(self.message)
