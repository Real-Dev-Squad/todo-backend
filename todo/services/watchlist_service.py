from datetime import datetime, timezone
from django.conf import settings
from django.urls import reverse_lazy
from urllib.parse import urlencode
import math

from todo.dto.responses.paginated_response import LinksData
from todo.dto.watchlist_dto import CreateWatchlistDTO, UpdateWatchlistDTO, WatchlistDTO
from todo.dto.responses.create_watchlist_response import CreateWatchlistResponse
from todo.dto.responses.get_watchlist_task_response import GetWatchlistTasksResponse
from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.watchlist import WatchlistModel
from todo.repositories.watchlist_repository import WatchlistRepository
from todo.repositories.task_repository import TaskRepository
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.utils.task_validation_utils import validate_task_exists
from bson import ObjectId


class PaginationConfig:
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]


class WatchlistService:
    @classmethod
    def get_watchlisted_tasks(
        cls,
        page: int,
        limit: int,
        user_id: str,
    ) -> GetWatchlistTasksResponse:
        try:
            count, tasks = WatchlistRepository.get_watchlisted_tasks(page, limit, user_id)

            if not tasks:
                return GetWatchlistTasksResponse(tasks=[], links=None)

            watchlisted_task_dtos = [cls.prepare_watchlisted_task_dto(task) for task in tasks]

            links = cls._build_pagination_links(page, limit, count)

            return GetWatchlistTasksResponse(tasks=watchlisted_task_dtos, links=links)

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

    @classmethod
    def add_task(cls, dto: CreateWatchlistDTO) -> CreateWatchlistResponse:
        try:
            # Validate that task exists using common function
            validate_task_exists(dto.taskId)

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

    @classmethod
    def update_task(cls, taskId: ObjectId, dto: UpdateWatchlistDTO, userId: ObjectId) -> CreateWatchlistResponse:
      
        validate_task_exists(str(taskId))

        updated_watchlist = WatchlistRepository.update(taskId, dto["isActive"], userId)
        if not updated_watchlist:
            raise TaskNotFoundException(taskId)

    @classmethod
    def prepare_watchlisted_task_dto(cls, watchlist_model: WatchlistDTO) -> WatchlistDTO:
        return WatchlistDTO(
            taskId=str(watchlist_model.taskId),
            displayId=watchlist_model.displayId,
            title=watchlist_model.title,
            description=watchlist_model.description,
            isAcknowledged=watchlist_model.isAcknowledged,
            isDeleted=watchlist_model.isDeleted,
            labels=watchlist_model.labels,
            dueAt=watchlist_model.dueAt,
            status=watchlist_model.status,
            priority=watchlist_model.priority,
            createdAt=watchlist_model.createdAt,
            createdBy=watchlist_model.createdBy,
            watchlistId=watchlist_model.watchlistId,
        )

    @classmethod
    def _build_pagination_links(cls, page: int, limit: int, total_count: int) -> LinksData:
        """Build pagination links with sort parameters"""

        total_pages = math.ceil(total_count / limit)
        next_link = None
        prev_link = None

        if page < total_pages:
            next_link = cls.build_page_url(page + 1, limit)

        if page > 1:
            prev_link = cls.build_page_url(page - 1, limit)

        return LinksData(next=next_link, prev=prev_link)

    @classmethod
    def build_page_url(cls, page: int, limit: int) -> str:
        base_url = reverse_lazy("watchlist")
        query_params = urlencode({"page": page, "limit": limit})
        return f"{base_url}?{query_params}"
