from datetime import datetime, timezone
from django.conf import settings

from todo.dto.watchlist_dto import CreateWatchlistDTO, WatchlistDTO
from todo.dto.responses.create_watchlist_response import CreateWatchlistResponse
from todo.dto.responses.get_watclist_task_response import GetWatchlistTasksResponse
from todo.models.watchlist import WatchlistModel
from todo.repositories.watchlist_repository import WatchlistRepository
from todo.repositories.task_repository import TaskRepository
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource


class PaginationConfig:
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]


class WatchlistService:
    @classmethod
    def get_tasks(
        cls,
        page: int,
        limit: int,
        user_id: str,
    ) -> GetWatchlistTasksResponse:
        try:
            [count, tasks] = WatchlistRepository.get_watchlisted_tasks(page, limit, user_id)

            if not tasks:
                return GetWatchlistTasksResponse(tasks=[], links=None)

            watchlisted_task_dtos = [cls.prepare_task_dto(task) for task in tasks]

            links = cls._build_pagination_links(page, limit, count)

            return GetWatchlistTasksResponse(tasks=watchlisted_task_dtos, links=links)

        except ValidationError as e:
            return GetWatchlistTasksResponse(
                tasks=[], links=None, error={"message": str(e), "code": "VALIDATION_ERROR"}
            )

        except Exception:
            return GetTasksResponse(
                tasks=[], links=None, error={"message": ApiErrors.UNEXPECTED_ERROR_OCCURRED, "code": "INTERNAL_ERROR"}
            )

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

    @classmethod
    def prepare_label_dto(cls, watchlist_model: WatchlistModel) -> WatchlistDTO:
        # created_by_dto = None
        # if watchlist_model.createdBy:
        #     if watchlist_model.createdBy == "system":
        #         created_by_dto = UserDTO(id="system", name="System")
        #     else:
        #         created_by_dto = UserDTO(id=watchlist_model.createdBy, name="User")

        # updated_by_dto = None
        # if watchlist_model.updatedBy:
        #     if watchlist_model.updatedBy == "system":
        #         updated_by_dto = UserDTO(id="system", name="System")
        #     else:
        #         updated_by_dto = UserDTO(id=watchlist_model.updatedBy, name="User")

        label_dtos = TaskService._prepare_label_dtos(task_model.labels) if task_model.labels else []
        created_by = TaskService.prepare_user_dto(task_model.createdBy) if task_model.createdBy else None
        updated_by = TaskService.prepare_user_dto(task_model.updatedBy) if task_model.updatedBy else None
        deferred_details = (
            TaskService.prepare_deferred_details_dto(task_model.deferredDetails) if task_model.deferredDetails else None
        )

        assignee_details = AssigneeTaskDetailsRepository.get_by_task_id(str(task_model.id))
        assignee_dto = TaskService._prepare_assignee_dto(assignee_details) if assignee_details else None

        return WatchlistDTO(
            taskId=str(watchlist_model.id),
            name=watchlist_model.name,
            displayId=watchlist_model.displayId,
            title=watchlist_model.title,
            description=watchlist_model.description,
            assignee=assignee_dto,
            isAcknowledged=watchlist_model.isAcknowledged,
            labels=label_dtos,
            startedAt=watchlist_model.startedAt,
            dueAt=watchlist_model.dueAt,
            status=watchlist_model.status,
            priority=watchlist_model.priority,
            deferredDetails=deferred_details,
            createdAt=watchlist_model.createdAt,
            updatedAt=watchlist_model.updatedAt,
            createdBy=created_by_dto,
            updatedBy=updated_by_dto,
        )
