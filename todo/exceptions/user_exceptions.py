from todo.constants.messages import ApiErrors


class UserNotFoundException(Exception):
    def __init__(self, user_id: str | None = None, message_template: str = ApiErrors.USER_NOT_FOUND):
        if user_id:
            self.message = message_template.format(user_id)
        else:
            self.message = ApiErrors.USER_NOT_FOUND_GENERIC
        super().__init__(self.message)
