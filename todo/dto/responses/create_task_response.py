from pydantic import BaseModel
from todo.dto.task_dto import TaskDTO


class CreateTaskResponse(BaseModel):
    statusCode: int = 201
    successMessage: str = "Task created successfully"
    data: TaskDTO
