from pydantic import BaseModel
from todo.dto.task_assignment_dto import TaskAssignmentResponseDTO


class CreateTaskAssignmentResponse(BaseModel):
    data: TaskAssignmentResponseDTO
    message: str = "Task assignment created successfully"
