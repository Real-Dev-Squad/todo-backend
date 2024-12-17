from typing import List

from todo.dto.responses.paginated_response import PaginatedResponse
from todo.dto.task_dto import TaskDTO


class GetTasksResponse(PaginatedResponse):
    tasks: List[TaskDTO] = []
