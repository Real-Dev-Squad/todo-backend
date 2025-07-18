from pydantic import BaseModel
from todo.dto.assignee_task_details_dto import AssigneeTaskDetailsDTO


class CreateTaskAssignmentResponse(BaseModel):
    data: AssigneeTaskDetailsDTO
    message: str = "Task assignment created successfully"
