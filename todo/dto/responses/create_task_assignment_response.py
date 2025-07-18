from pydantic import BaseModel
from todo.dto.task_assignment_dto import TaskAssignmentDTO


class CreateTaskAssignmentResponse(BaseModel):
    data: TaskAssignmentDTO
    message: str = "Task assignment created successfully"
