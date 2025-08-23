from datetime import datetime, timezone
from django.conf import settings
from django.urls import reverse_lazy
from urllib.parse import urlencode
import math

from todo.constants.task import TaskStatus
from todo.dto.label_dto import LabelDTO
from todo.dto.responses.paginated_response import LinksData
from todo.dto.watchlist_dto import CreateWatchlistDTO, UpdateWatchlistDTO, WatchlistDTO
from todo.dto.responses.create_watchlist_response import CreateWatchlistResponse
from todo.dto.responses.get_watchlist_task_response import GetWatchlistTasksResponse
from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.watchlist import WatchlistModel
from todo.repositories.label_repository import LabelRepository
from todo.repositories.watchlist_repository import WatchlistRepository
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.utils.task_validation_utils import validate_task_exists
from bson import ObjectId
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService


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

            dual_write_service = EnhancedDualWriteService()
            watchlist_data = {
                "task_id": str(created_watchlist.taskId),
                "user_id": str(created_watchlist.userId),
                "created_by": str(created_watchlist.createdBy),
                "created_at": created_watchlist.createdAt,
                "updated_at": created_watchlist.updatedAt,
            }

            dual_write_success = dual_write_service.create_document(
                collection_name="watchlists", data=watchlist_data, mongo_id=str(created_watchlist.id)
            )

            if not dual_write_success:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to sync watchlist {created_watchlist.id} to Postgres")
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

        dual_write_service = EnhancedDualWriteService()
        watchlist_data = {
            "task_id": str(updated_watchlist["taskId"]),
            "user_id": str(updated_watchlist["userId"]),
            "created_by": str(updated_watchlist["createdBy"]),
            "created_at": updated_watchlist["createdAt"],
            "updated_at": updated_watchlist["updatedAt"],
        }

        dual_write_success = dual_write_service.update_document(
            collection_name="watchlists", mongo_id=str(taskId), data=watchlist_data
        )

        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync watchlist update {taskId} to Postgres")

        return CreateWatchlistResponse(data=updated_watchlist)

    @classmethod
    def _prepare_label_dtos(cls, label_ids: list[str]) -> list[LabelDTO]:
        object_ids = [ObjectId(id) for id in label_ids]  # Convert here!
        label_models = LabelRepository.list_by_ids(object_ids)

        return [
            LabelDTO(
                id=str(label_model.id),
                name=label_model.name,
                color=label_model.color,
            )
            for label_model in label_models
        ]

    @classmethod
    def prepare_watchlisted_task_dto(cls, watchlist_model: WatchlistDTO) -> WatchlistDTO:
        labels = cls._prepare_label_dtos(watchlist_model.labels) if watchlist_model.labels else []

        # Handle assignee data if present
        assignee = None
        if hasattr(watchlist_model, "assignee") and watchlist_model.assignee:
            assignee = watchlist_model.assignee

        task_status = watchlist_model.status

        if watchlist_model.deferredDetails and watchlist_model.deferredDetails.deferredTill > datetime.now(
            timezone.utc
        ):
            task_status = TaskStatus.DEFERRED.value

        return WatchlistDTO(
            taskId=str(watchlist_model.taskId),
            displayId=watchlist_model.displayId,
            title=watchlist_model.title,
            description=watchlist_model.description,
            isAcknowledged=watchlist_model.isAcknowledged,
            isDeleted=watchlist_model.isDeleted,
            labels=labels,
            dueAt=watchlist_model.dueAt,
            deferredDetails=watchlist_model.deferredDetails,
            status=task_status,
            priority=watchlist_model.priority,
            createdAt=watchlist_model.createdAt,
            createdBy=watchlist_model.createdBy,
            watchlistId=watchlist_model.watchlistId,
            assignee=assignee,
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
