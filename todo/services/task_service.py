from typing import List
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from rest_framework.exceptions import ValidationError as DRFValidationError
from todo.dto.deferred_details_dto import DeferredDetailsDTO
from todo.dto.label_dto import LabelDTO
from todo.dto.task_dto import TaskDTO, CreateTaskDTO
from todo.dto.user_dto import UserDTO
from todo.dto.assignee_task_details_dto import AssigneeInfoDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.dto.responses.paginated_response import LinksData
from todo.exceptions.user_exceptions import UserNotFoundException
from todo.models import Task
from todo.models import AssigneeTaskDetails
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.postgres_task_repository import TaskRepository
from todo.repositories.postgres_label_repository import LabelRepository
from todo.repositories.postgres_assignee_task_details_repository import AssigneeTaskDetailsRepository
from todo.repositories.postgres_team_repository import TeamRepository
from todo.constants.task import (
    TaskStatus,
    TaskPriority,
    MINIMUM_DEFERRAL_NOTICE_DAYS,
)
from todo.constants.messages import ApiErrors, ValidationErrors
from django.conf import settings
from todo.exceptions.task_exceptions import (
    TaskNotFoundException,
    UnprocessableEntityException,
    TaskStateConflictException,
)
from bson.errors import InvalidId as BsonInvalidId

from todo.repositories.postgres_user_repository import UserRepository
import math


@dataclass
class PaginationConfig:
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]


class TaskService:
    DIRECT_ASSIGNMENT_FIELDS = {"title", "description", "dueAt", "startedAt", "isAcknowledged"}

    @classmethod
    def get_tasks(
        cls,
        page: int,
        limit: int,
        sort_by: str,
        order: str,
        user_id: str,
    ) -> GetTasksResponse:
        try:
            cls._validate_pagination_params(page, limit)

            tasks = TaskRepository.list(page, limit, sort_by, order, user_id)

            total_count = TaskRepository.count(user_id)

            if not tasks:
                return GetTasksResponse(tasks=[], links=None)

            task_dtos = [cls.prepare_task_dto(task) for task in tasks]

            links = cls._build_pagination_links(page, limit, total_count, sort_by, order)

            return GetTasksResponse(tasks=task_dtos, links=links)

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
    def _build_pagination_links(cls, page: int, limit: int, total_count: int, sort_by: str, order: str) -> LinksData:
        """Build pagination links with sort parameters"""

        total_pages = math.ceil(total_count / limit)
        next_link = None
        prev_link = None

        if page < total_pages:
            next_link = cls.build_page_url(page + 1, limit, sort_by, order)

        if page > 1:
            prev_link = cls.build_page_url(page - 1, limit, sort_by, order)

        return LinksData(next=next_link, prev=prev_link)

    @classmethod
    def build_page_url(cls, page: int, limit: int, sort_by: str, order: str) -> str:
        base_url = reverse_lazy("tasks")
        query_params = urlencode({"page": page, "limit": limit, "sort_by": sort_by, "order": order})
        return f"{base_url}?{query_params}"

    @classmethod
    def prepare_task_dto(cls, task_model: Task) -> TaskDTO:
        label_dtos = cls._prepare_label_dtos(task_model.labels) if task_model.labels else []
        created_by = cls.prepare_user_dto(task_model.created_by) if task_model.created_by else None
        updated_by = cls.prepare_user_dto(task_model.updated_by) if task_model.updated_by else None
        deferred_details = cls.prepare_deferred_details_dto(task_model)

        assignee_details = AssigneeTaskDetailsRepository.get_by_task_id(str(task_model.id))
        assignee_dto = cls._prepare_assignee_dto(assignee_details) if assignee_details else None

        return TaskDTO(
            id=str(task_model.id),
            displayId=task_model.displayId,
            title=task_model.title,
            description=task_model.description,
            assignee=assignee_dto,
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
    def _prepare_assignee_dto(cls, assignee_details: AssigneeTaskDetails) -> AssigneeInfoDTO:
        """Prepare assignee DTO from assignee task details."""
        assignee_id = str(assignee_details.assignee_id)

        # Get assignee details based on relation type
        if assignee_details.relation_type == "user":
            assignee = UserRepository.get_by_id(assignee_id)
        elif assignee_details.relation_type == "team":
            assignee = TeamRepository.get_by_id(assignee_id)
        else:
            return None

        if not assignee:
            return None

        return AssigneeInfoDTO(
            id=assignee_id,
            name=assignee.name,
            relation_type=assignee_details.relation_type,
            is_action_taken=assignee_details.is_action_taken,
            is_active=assignee_details.is_active,
        )

    @classmethod
    def prepare_deferred_details_dto(cls, task: Task) -> DeferredDetailsDTO | None:
        if not task.deferred_at or not task.deferred_till or not task.deferred_by:
            return None

        deferred_by_user = cls.prepare_user_dto(task.deferred_by)

        return DeferredDetailsDTO(
            deferredAt=task.deferred_at,
            deferredTill=task.deferred_till,
            deferredBy=deferred_by_user,
        )

    @classmethod
    def prepare_user_dto(cls, user_id: str) -> UserDTO:
        user = UserRepository.get_by_id(user_id)
        if user:
            return UserDTO(id=str(user_id), name=user.name)
        raise UserNotFoundException(user_id)

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
    def update_task(cls, task_id: str, validated_data: dict, user_id: str) -> TaskDTO:
        current_task = TaskRepository.get_by_id(task_id)

        if not current_task:
            raise TaskNotFoundException(task_id)

        # Check if user is the creator
        if current_task.createdBy != user_id:
            # Check if user is assigned to this task
            assigned_task_ids = TaskRepository._get_assigned_task_ids_for_user(user_id)
            if current_task.id not in assigned_task_ids:
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)

        # Handle assignee updates if provided
        if validated_data.get("assignee"):
            assignee_info = validated_data["assignee"]
            assignee_id = assignee_info.get("assignee_id")
            relation_type = assignee_info.get("relation_type")

            if relation_type == "user":
                assignee_data = UserRepository.get_by_id(assignee_id)
                if not assignee_data:
                    raise UserNotFoundException(assignee_id)
            elif relation_type == "team":
                team_data = TeamRepository.get_by_id(assignee_id)
                if not team_data:
                    raise ValueError(f"Team not found: {assignee_id}")

        update_payload = {}
        enum_fields = {"priority": TaskPriority, "status": TaskStatus}

        for field, value in validated_data.items():
            if field == "labels":
                update_payload[field] = cls._process_labels_for_update(value)
            elif field in enum_fields:
                update_payload[field] = cls._process_enum_for_update(enum_fields[field], value)
            elif field in cls.DIRECT_ASSIGNMENT_FIELDS:
                update_payload[field] = value

        # Handle assignee updates separately
        if "assignee" in validated_data:
            assignee_info = validated_data["assignee"]
            AssigneeTaskDetailsRepository.update_assignee(
                task_id, assignee_info["assignee_id"], assignee_info["relation_type"], user_id
            )

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

        # Check if user is the creator
        if current_task.createdBy != user_id:
            # Check if user is assigned to this task
            assigned_task_ids = TaskRepository._get_assigned_task_ids_for_user(user_id)
            if current_task.id not in assigned_task_ids:
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)

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

        update_payload = {
            "deferred_at": datetime.now(timezone.utc),
            "deferred_till": deferred_till,
            "deferred_by": user_id,
            "updated_by": user_id,
        }

        updated_task = TaskRepository.update(task_id, update_payload)
        if not updated_task:
            raise TaskNotFoundException(task_id)

        return cls.prepare_task_dto(updated_task)

    @classmethod
    def create_task(cls, dto: CreateTaskDTO) -> CreateTaskResponse:
        now = datetime.now(timezone.utc)
        started_at = now if dto.status == TaskStatus.IN_PROGRESS else None

        # Validate assignee
        if dto.assignee:
            assignee_id = dto.assignee.get("assignee_id")
            relation_type = dto.assignee.get("relation_type")

            if relation_type == "user":
                user = UserRepository.get_by_id(assignee_id)
                if not user:
                    raise UserNotFoundException(assignee_id)
            elif relation_type == "team":
                team = TeamRepository.get_by_id(assignee_id)
                if not team:
                    raise ValueError(f"Team not found: {assignee_id}")

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

        task = Task(
            id=None,
            title=dto.title,
            description=dto.description,
            priority=dto.priority,
            status=dto.status,
            labels=dto.labels,
            dueAt=dto.dueAt,
            startedAt=started_at,
            createdAt=now,
            isAcknowledged=False,
            isDeleted=False,
            createdBy=dto.createdBy,  # placeholder, will be user_id when auth is in place
        )

        try:
            created_task = TaskRepository.create(task)

            # Create assignee relationship if assignee is provided
            if dto.assignee:
                assignee_relationship = AssigneeTaskDetails(
                    assignee_id=PyObjectId(dto.assignee["assignee_id"]),
                    task_id=created_task.id,
                    relation_type=dto.assignee["relation_type"],
                    created_by=PyObjectId(dto.createdBy),
                    updated_by=None,
                )
                AssigneeTaskDetailsRepository.create(assignee_relationship)

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
    def delete_task(cls, task_id: str, user_id: str) -> None:
        deleted_task_model = TaskRepository.delete_by_id(task_id, user_id)
        if deleted_task_model is None:
            raise TaskNotFoundException(task_id)
        return None

    @classmethod
    def get_tasks_for_user(
        cls, user_id: str, page: int = PaginationConfig.DEFAULT_PAGE, limit: int = PaginationConfig.DEFAULT_LIMIT
    ) -> GetTasksResponse:
        cls._validate_pagination_params(page, limit)
        tasks = TaskRepository.get_tasks_for_user(user_id, page, limit)
        if not tasks:
            return GetTasksResponse(tasks=[], links=None)

        task_dtos = [cls.prepare_task_dto(task) for task in tasks]
        return GetTasksResponse(tasks=task_dtos, links=None)
