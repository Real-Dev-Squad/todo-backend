from typing import List
from dataclasses import dataclass
from django.core.paginator import Paginator, EmptyPage
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from urllib.parse import urlencode
from datetime import datetime, timezone

from todo.dto.label_dto import LabelDTO
from todo.dto.task_dto import TaskDTO, CreateTaskDTO
from todo.dto.user_dto import UserDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.dto.responses.paginated_response import LinksData
from todo.models.task import TaskModel
from todo.repositories.task_repository import TaskRepository
from todo.repositories.label_repository import LabelRepository
from todo.constants.task import TaskStatus
from todo.constants.messages import ApiErrors, ValidationErrors
from django.conf import settings


@dataclass
class PaginationConfig:
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]


class TaskService:
    @classmethod
    def get_tasks(
        cls, page: int = PaginationConfig.DEFAULT_PAGE, limit: int = PaginationConfig.DEFAULT_LIMIT
    ) -> GetTasksResponse:
        try:
            cls._validate_pagination_params(page, limit)

            tasks = TaskRepository.get_all()

            if not tasks:
                return GetTasksResponse(tasks=[], links=None)

            paginator = Paginator(tasks, limit)

            try:
                current_page = paginator.page(page)

                task_dtos = [cls.prepare_task_dto(task) for task in current_page.object_list]

                links = cls._prepare_pagination_links(current_page=current_page, page=page, limit=limit)

                return GetTasksResponse(tasks=task_dtos, links=links)

            except EmptyPage:
                return GetTasksResponse(
                    tasks=[],
                    links=None,
                    error={"message": "Requested page exceeds available results", "code": "PAGE_NOT_FOUND"},
                )

        except ValidationError as e:
            return GetTasksResponse(tasks=[], links=None, error={"message": str(e), "code": "VALIDATION_ERROR"})

        except Exception:
            return GetTasksResponse(
                tasks=[], links=None, error={"message": "An unexpected error occurred", "code": "INTERNAL_ERROR"}
            )

    @classmethod
    def _validate_pagination_params(cls, page: int, limit: int) -> None:
        if page < 1:
            raise ValidationError("Page must be a positive integer")

        if limit < 1:
            raise ValidationError("Limit must be a positive integer")

        if limit > PaginationConfig.MAX_LIMIT:
            raise ValidationError(f"Maximum limit of {PaginationConfig.MAX_LIMIT} exceeded")

    @classmethod
    def _prepare_pagination_links(cls, current_page, page: int, limit: int) -> LinksData:
        next_link = None
        prev_link = None

        if current_page.has_next():
            next_page = current_page.next_page_number()
            next_link = cls.build_page_url(next_page, limit)

        if current_page.has_previous():
            prev_page = current_page.previous_page_number()
            prev_link = cls.build_page_url(prev_page, limit)

        return LinksData(next=next_link, prev=prev_link)

    @classmethod
    def build_page_url(cls, page: int, limit: int) -> str:
        base_url = reverse_lazy("tasks")
        query_params = urlencode({"page": page, "limit": limit})
        return f"{base_url}?{query_params}"

    @classmethod
    def prepare_task_dto(cls, task_model: TaskModel) -> TaskDTO:
        label_dtos = cls._prepare_label_dtos(task_model.labels) if task_model.labels else []

        assignee = cls.prepare_user_dto(task_model.assignee) if task_model.assignee else None
        created_by = cls.prepare_user_dto(task_model.createdBy)
        updated_by = cls.prepare_user_dto(task_model.updatedBy) if task_model.updatedBy else None

        return TaskDTO(
            id=str(task_model.id),
            displayId=task_model.displayId,
            title=task_model.title,
            description=task_model.description,
            assignee=assignee,
            isAcknowledged=task_model.isAcknowledged,
            labels=label_dtos,
            startedAt=task_model.startedAt,
            dueAt=task_model.dueAt,
            status=task_model.status,
            priority=task_model.priority,
            createdAt=task_model.createdAt,
            updatedAt=task_model.updatedAt,
            createdBy=created_by,
            updatedBy=updated_by,
        )

    @classmethod
    def _prepare_label_dtos(cls, label_ids: List[str]) -> List[LabelDTO]:
        label_models = LabelRepository.list_by_ids(label_ids)

        return [
            LabelDTO(
                name=label_model.name,
                color=label_model.color,
                createdAt=label_model.createdAt,
                updatedAt=label_model.updatedAt if hasattr(label_model, "updatedAt") else None,
                createdBy=cls.prepare_user_dto(label_model.createdBy),
                updatedBy=cls.prepare_user_dto(label_model.updatedBy)
                if hasattr(label_model, "updatedBy") and label_model.updatedBy
                else None,
            )
            for label_model in label_models
        ]

    @classmethod
    def prepare_user_dto(cls, user_id: str) -> UserDTO:
        return UserDTO(id=user_id, name="SYSTEM")

    @classmethod
    def create_task(cls, dto: CreateTaskDTO) -> CreateTaskResponse:
        now = datetime.now(timezone.utc)
        started_at = now if dto.status == TaskStatus.IN_PROGRESS else None

        if dto.labels:
            existing_labels = LabelRepository.list_by_ids(dto.labels)
            if len(existing_labels) != len(dto.labels):
                found_ids = [str(label.id) for label in existing_labels]
                missing_ids = [label_id for label_id in dto.labels if label_id not in found_ids]

                raise ValueError(
                    ApiErrorResponse(
                        statusCode=400,
                        message=ApiErrors.INVALID_LABELS,
                        errors=[
                            ApiErrorDetail(
                                source={ApiErrorSource.PARAMETER: "labels"},
                                title=ApiErrors.INVALID_LABEL_IDS,
                                detail=ValidationErrors.MISSING_LABEL_IDS.format(", ".join(missing_ids)),
                            )
                        ],
                    )
                )

        task = TaskModel(
            title=dto.title,
            description=dto.description,
            priority=dto.priority,
            status=dto.status,
            assignee=dto.assignee,
            labels=dto.labels,
            dueAt=dto.dueAt,
            startedAt=started_at,
            createdAt=now,
            isAcknowledged=False,
            isDeleted=False,
            createdBy="system",  # placeholder, will be user_id when auth is in place
        )

        try:
            created_task = TaskRepository.create(task)
            task_dto = cls.prepare_task_dto(created_task)
            return CreateTaskResponse(data=task_dto)
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
