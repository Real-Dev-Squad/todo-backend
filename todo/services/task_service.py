from typing import List
from dataclasses import dataclass
from django.core.paginator import Paginator, EmptyPage
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from rest_framework.exceptions import ValidationError as DRFValidationError
from todo.dto.deferred_details_dto import DeferredDetailsDTO
from todo.dto.label_dto import LabelDTO
from todo.dto.task_dto import TaskDTO, CreateTaskDTO
from todo.dto.user_dto import UserDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.dto.responses.paginated_response import LinksData
from todo.models.task import TaskModel, DeferredDetailsModel
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.task_repository import TaskRepository
from todo.repositories.label_repository import LabelRepository
from todo.constants.task import TaskStatus, TaskPriority, MINIMUM_DEFERRAL_NOTICE_DAYS
from todo.constants.messages import ApiErrors, ValidationErrors
from django.conf import settings
from todo.exceptions.task_exceptions import (
    TaskNotFoundException,
    UnprocessableEntityException,
    TaskStateConflictException,
)
from bson.errors import InvalidId as BsonInvalidId


@dataclass
class PaginationConfig:
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]


class TaskService:
    DIRECT_ASSIGNMENT_FIELDS = {"title", "description", "assignee", "dueAt", "startedAt", "isAcknowledged"}

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
                    error={"message": ApiErrors.PAGE_NOT_FOUND, "code": "PAGE_NOT_FOUND"},
                )

        except ValidationError as e:
            return GetTasksResponse(tasks=[], links=None, error={"message": str(e), "code": "VALIDATION_ERROR"})

        except Exception:
            return GetTasksResponse(
                tasks=[], links=None, error={"message": ApiErrors.UNEXPECTED_ERROR_OCCURRED, "code": "INTERNAL_ERROR"}
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
        deferred_details = (
            cls.prepare_deferred_details_dto(task_model.deferredDetails) if task_model.deferredDetails else None
        )

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
            deferredDetails=deferred_details,
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
                id=str(label_model.id),
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
    def prepare_deferred_details_dto(cls, deferred_details_model: DeferredDetailsModel) -> DeferredDetailsDTO | None:
        if not deferred_details_model:
            return None

        deferred_by_user = cls.prepare_user_dto(deferred_details_model.deferredBy)

        return DeferredDetailsDTO(
            deferredAt=deferred_details_model.deferredAt,
            deferredTill=deferred_details_model.deferredTill,
            deferredBy=deferred_by_user,
        )

    @classmethod
    def prepare_user_dto(cls, user_id: str) -> UserDTO:
        return UserDTO(id=user_id, name="SYSTEM")

    @classmethod
    def get_task_by_id(cls, task_id: str) -> TaskDTO:
        try:
            task_model = TaskRepository.get_by_id(task_id)
            if not task_model:
                raise TaskNotFoundException(task_id)
            return cls.prepare_task_dto(task_model)
        except BsonInvalidId as exc:
            raise exc

    @classmethod
    def _process_labels_for_update(cls, raw_labels: list | None) -> list[PyObjectId]:
        if raw_labels is None:
            return []

        label_object_ids = [PyObjectId(label_id_str) for label_id_str in raw_labels]

        if label_object_ids:
            existing_labels = LabelRepository.list_by_ids(label_object_ids)
            if len(existing_labels) != len(label_object_ids):
                found_db_ids_str = {str(label.id) for label in existing_labels}
                missing_ids_str = [str(py_id) for py_id in label_object_ids if str(py_id) not in found_db_ids_str]
                raise DRFValidationError(
                    {"labels": [ValidationErrors.MISSING_LABEL_IDS.format(", ".join(missing_ids_str))]}
                )
        return label_object_ids

    @classmethod
    def _process_enum_for_update(cls, enum_type: type, value: str | None) -> str | None:
        if value is None:
            return None
        return enum_type[value].value

    @classmethod
    def update_task(cls, task_id: str, validated_data: dict, user_id: str = "system") -> TaskDTO:
        current_task = TaskRepository.get_by_id(task_id)
        if not current_task:
            raise TaskNotFoundException(task_id)

        update_payload = {}
        enum_fields = {"priority": TaskPriority, "status": TaskStatus}

        for field, value in validated_data.items():
            if field == "labels":
                update_payload[field] = cls._process_labels_for_update(value)
            elif field in enum_fields:
                update_payload[field] = cls._process_enum_for_update(enum_fields[field], value)
            elif field in cls.DIRECT_ASSIGNMENT_FIELDS:
                update_payload[field] = value

        if not update_payload:
            return cls.prepare_task_dto(current_task)

        update_payload["updatedBy"] = user_id
        updated_task = TaskRepository.update(task_id, update_payload)

        if not updated_task:
            raise TaskNotFoundException(task_id)

        return cls.prepare_task_dto(updated_task)

    @classmethod
    def defer_task(cls, task_id: str, deferred_till: datetime, user_id: str) -> TaskDTO:
        current_task = TaskRepository.get_by_id(task_id)
        if not current_task:
            raise TaskNotFoundException(task_id)

        if current_task.status == TaskStatus.DONE:
            raise TaskStateConflictException(ValidationErrors.CANNOT_DEFER_A_DONE_TASK)

        if deferred_till.tzinfo is None:
            deferred_till = deferred_till.replace(tzinfo=timezone.utc)

        if current_task.dueAt:
            due_at = (
                current_task.dueAt.replace(tzinfo=timezone.utc)
                if current_task.dueAt.tzinfo is None
                else current_task.dueAt.astimezone(timezone.utc)
            )

            defer_limit = due_at - timedelta(days=MINIMUM_DEFERRAL_NOTICE_DAYS)

            if deferred_till > defer_limit:
                raise UnprocessableEntityException(
                    ValidationErrors.CANNOT_DEFER_TOO_CLOSE_TO_DUE_DATE,
                    source={ApiErrorSource.PARAMETER: "deferredTill"},
                )

        deferred_details = DeferredDetailsModel(
            deferredAt=datetime.now(timezone.utc),
            deferredTill=deferred_till,
            deferredBy=user_id,
        )

        update_payload = {
            "deferredDetails": deferred_details.model_dump(),
            "updatedBy": user_id,
        }

        updated_task = TaskRepository.update(task_id, update_payload)
        if not updated_task:
            raise TaskNotFoundException(task_id)

        return cls.prepare_task_dto(updated_task)

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
            id=None,
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

    @classmethod
    def delete_task(cls, task_id: str) -> None:
        deleted_task_model = TaskRepository.delete_by_id(task_id)
        if deleted_task_model is None:
            raise TaskNotFoundException(task_id)
        return None
