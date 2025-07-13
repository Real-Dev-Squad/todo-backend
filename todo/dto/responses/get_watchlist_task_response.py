from typing import List

from todo.dto.responses.paginated_response import PaginatedResponse
from todo.dto.watchlist_dto import WatchlistDTO


class GetWatchlistTasksResponse(PaginatedResponse):
    tasks: List[WatchlistDTO] = []
