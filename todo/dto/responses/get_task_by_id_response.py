from pydantic import BaseModel
from todo.dto.task_dto import TaskDTO


class GetTaskByIdResponse(BaseModel):
    data: TaskDTO
