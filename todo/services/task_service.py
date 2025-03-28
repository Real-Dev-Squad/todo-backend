from typing import List
from dataclasses import dataclass
from django.core.paginator import Paginator, EmptyPage
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from urllib.parse import urlencode

from todo.dto.label_dto import LabelDTO
from todo.dto.task_dto import TaskDTO
from todo.dto.user_dto import UserDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.paginated_response import LinksData
from todo.models.task import TaskModel
from todo.repositories.task_repository import TaskRepository
from todo.repositories.label_repository import LabelRepository
from django.conf import settings


@dataclass
class PaginationConfig:
    """Configuration for pagination parameters"""
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]


class TaskService:
    @classmethod
    def get_tasks(
        cls, 
        page: int = PaginationConfig.DEFAULT_PAGE, 
        limit: int = PaginationConfig.DEFAULT_LIMIT
    ) -> GetTasksResponse:
        """
        Retrieves tasks with pagination.
        
        Args:
            page: Page number (starts from 1)
            limit: Number of items per page
            
        Returns:
            GetTasksResponse with tasks and pagination links
        """
        try:

            cls._validate_pagination_params(page, limit)
            

            tasks = TaskRepository.get_all()

            if not tasks:
                return GetTasksResponse(tasks=[], links=None)
                

            paginator = Paginator(tasks, limit)
            
            try:

                current_page = paginator.page(page)
                

                task_dtos = [cls.prepare_task_dto(task) for task in current_page.object_list]
                

                links = cls._prepare_pagination_links(
                    current_page=current_page,
                    page=page,
                    limit=limit
                )
                
                return GetTasksResponse(tasks=task_dtos, links=links)
                
            except EmptyPage:
                return GetTasksResponse(tasks=[], links=None)
                
        except ValidationError:

            return GetTasksResponse(tasks=[], links=None)
            
        except Exception:

            return GetTasksResponse(tasks=[], links=None)

    @classmethod
    def _validate_pagination_params(cls, page: int, limit: int) -> None:
        """
        Validates pagination parameters.
        
        Args:
            page: Page number
            limit: Number of items per page
            
        Raises:
            ValidationError: If pagination parameters are invalid
        """
        if page < 1:
            raise ValidationError("Page must be a positive integer")
            
        if limit < 1:
            raise ValidationError("Limit must be a positive integer")
            
        if limit > PaginationConfig.MAX_LIMIT:
            raise ValidationError(f"Maximum limit of {PaginationConfig.MAX_LIMIT} exceeded")

    @classmethod
    def _prepare_pagination_links(cls, current_page, page: int, limit: int) -> LinksData:
        """
        Prepares pagination links for the response.
        
        Args:
            current_page: Django Paginator page object
            page: Current page number
            limit: Number of items per page
            
        Returns:
            LinksData with next and prev links
        """
        next_link = None
        prev_link = None
        
        if current_page.has_next():
            next_page = current_page.next_page_number()
            next_link = cls._build_page_url(next_page, limit)
            
        if current_page.has_previous():
            prev_page = current_page.previous_page_number()
            prev_link = cls._build_page_url(prev_page, limit)
            
        return LinksData(next=next_link, prev=prev_link)

    @classmethod
    def _build_page_url(cls, page: int, limit: int) -> str:
        """
        Builds a URL for a specific page with pagination parameters.
        
        Args:
            page: Page number
            limit: Number of items per page
            
        Returns:
            URL string with pagination parameters
        """
        base_url = reverse_lazy('tasks')
        query_params = urlencode({'page': page, 'limit': limit})
        return f"{base_url}?{query_params}"

    @classmethod
    def prepare_task_dto(cls, task_model: TaskModel) -> TaskDTO:
        """
        Maps a TaskModel to a TaskDTO.
        
        Args:
            task_model: Task model instance
            
        Returns:
            TaskDTO with data from the model
        """
        label_dtos = cls._prepare_label_dtos(task_model.labels) if task_model.labels else []
        
        assignee = cls.prepare_user_dto(task_model.assignee) if task_model.assignee else None
        created_by = cls.prepare_user_dto(task_model.createdBy) if task_model.createdBy else None
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
        """
        Prepares label DTOs from label IDs.
        
        Args:
            label_ids: List of label IDs
            
        Returns:
            List of LabelDTO objects
        """
        label_models = LabelRepository.list_by_ids(label_ids)
        
        return [
            LabelDTO(
                name=label_model.name,
                color=label_model.color,
                createdAt=label_model.createdAt,
                updatedAt=label_model.updatedAt if hasattr(label_model, 'updatedAt') else None,
                createdBy=cls.prepare_user_dto(label_model.createdBy) if hasattr(label_model, 'createdBy') and label_model.createdBy else None,
                updatedBy=cls.prepare_user_dto(label_model.updatedBy) if hasattr(label_model, 'updatedBy') and label_model.updatedBy else None,
            )
            for label_model in label_models
        ]

    @classmethod
    def prepare_user_dto(cls, user_id: str) -> UserDTO:
        """
        Maps a user ID to a UserDTO.
        
        Args:
            user_id: User ID
            
        Returns:
            UserDTO with data from the user ID
        """

        return UserDTO(id=user_id, name="SYSTEM")
