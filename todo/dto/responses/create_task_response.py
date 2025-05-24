from pydantic import BaseModel
from todo.dto.task_dto import TaskDTO
from todo.constants.messages import AppMessages


class CreateTaskResponse(BaseModel):
    statusCode: int = 201
    successMessage: str = AppMessages.TASK_CREATED
    data: TaskDTO
