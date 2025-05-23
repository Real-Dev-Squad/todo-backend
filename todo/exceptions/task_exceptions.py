class TaskNotFoundException(Exception):
    def __init__(self, message: str = "Task not found"):
        super().__init__(message)
