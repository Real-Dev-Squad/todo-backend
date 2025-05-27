from todo.constants.messages import ValidationErrors


class TaskNotFoundException(Exception):
    def __init__(self, message: str = ValidationErrors.TASK_NOT_FOUND):
        super().__init__(message)
