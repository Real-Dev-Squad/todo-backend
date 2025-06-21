from todo.constants.messages import ApiErrors


class TaskNotFoundException(Exception):
    def __init__(self, task_id: str | None = None, message_template: str = ApiErrors.TASK_NOT_FOUND):
        if task_id:
            self.message = message_template.format(task_id)
        else:
            self.message = ApiErrors.TASK_NOT_FOUND_GENERIC
        super().__init__(self.message)


class UnprocessableEntityException(Exception):
    def __init__(self, message: str, source: dict | None = None):
        self.message = message
        self.source = source
        super().__init__(self.message)


class TaskStateConflictException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
