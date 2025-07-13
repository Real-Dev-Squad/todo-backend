from pydantic import BaseModel
from todo.dto.watchlist_dto import CreateWatchlistDTO
from todo.constants.messages import AppMessages


class CreateWatchlistResponse(BaseModel):
    statusCode: int = 201
    successMessage: str = AppMessages.WATCHLIST_CREATED
    data: CreateWatchlistDTO
