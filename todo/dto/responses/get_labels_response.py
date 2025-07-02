from typing import List

from todo.dto.label_dto import LabelDTO
from todo.dto.responses.paginated_response import PaginatedResponse


class GetLabelsResponse(PaginatedResponse):
    labels: List[LabelDTO] = []
    total: int = 0
    page: int = 1
    limit: int = 10
