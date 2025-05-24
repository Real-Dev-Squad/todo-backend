from todo.constants.messages import ApiErrors


class TaskNotFoundException(Exception):
    def __init__(self, message: str = ApiErrors.TASK_NOT_FOUND_TITLE):
        super().__init__(message)
