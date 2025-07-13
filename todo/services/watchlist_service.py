from datetime import datetime, timezone
from django.conf import settings

from todo.dto.watchlist_dto import CreateWatchlistDTO
from todo.dto.responses.create_watchlist_response import CreateWatchlistResponse
from todo.models.watchlist import WatchlistModel
from todo.repositories.watchlist_repository import WatchlistRepository
from todo.repositories.task_repository import TaskRepository
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource


class WatchlistService:
    @classmethod
    def add_task(cls, dto: CreateWatchlistDTO) -> CreateWatchlistResponse:
        try:
            TaskRepository.get_by_id(dto.taskId)

            existing = WatchlistRepository.get_by_user_and_task(dto.userId, dto.taskId)
            if existing:
                raise ValueError(
                    ApiErrorResponse(
                        statusCode=400,
                        message=ApiErrors.TASK_ALREADY_IN_WATCHLIST,
                        errors=[
                            ApiErrorDetail(
                                source={ApiErrorSource.PARAMETER: "taskId"},
                                title=ApiErrors.VALIDATION_ERROR,
                                detail=ApiErrors.TASK_ALREADY_IN_WATCHLIST,
                            )
                        ],
                    )
                )

            watchlist_model = WatchlistModel(
                taskId=dto.taskId,
                userId=dto.userId,
                createdBy=dto.createdBy,
                createdAt=datetime.now(timezone.utc),
            )
            created_watchlist = WatchlistRepository.create(watchlist_model)
            watchlist_dto = CreateWatchlistDTO(
                taskId=created_watchlist.taskId,
                userId=created_watchlist.userId,
                createdBy=created_watchlist.createdBy,
                createdAt=created_watchlist.createdAt,
            )
            return CreateWatchlistResponse(data=watchlist_dto)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                raise e
            raise ValueError(
                ApiErrorResponse(
                    statusCode=500,
                    message=ApiErrors.REPOSITORY_ERROR,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: "task_repository"},
                            title=ApiErrors.UNEXPECTED_ERROR,
                            detail=str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR,
                        )
                    ],
                )
            )
        except Exception as e:
            raise ValueError(
                ApiErrorResponse(
                    statusCode=500,
                    message=ApiErrors.SERVER_ERROR,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: "server"},
                            title=ApiErrors.UNEXPECTED_ERROR,
                            detail=str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR,
                        )
                    ],
                )
            )
