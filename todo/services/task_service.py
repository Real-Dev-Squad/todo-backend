from django.urls import reverse_lazy
from django.conf import settings
from todo.dto.label_dto import LabelDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.paginated_response import LinksData
from todo.dto.task_dto import TaskDTO
from todo.dto.user_dto import UserDTO
from todo.models.task import TaskModel
from todo.repositories.label_repository import LabelRepository
from todo.repositories.task_repository import TaskRepository


class TaskService:
    tasks_api_base_url = reverse_lazy("tasks")

    @classmethod
    def get_tasks(cls, page=1, limit=settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"]) -> GetTasksResponse:
        response = GetTasksResponse()
        tasks_count = TaskRepository.count()
        tasks_skip_count = (page - 1) * limit
        if tasks_count <= tasks_skip_count:
            return response

        tasks = TaskRepository.list(page, limit)
        task_dicts = list(map(cls.prepare_task_dto, tasks))
        response.tasks = task_dicts
        links_data = LinksData()
        if page > 1:
            links_data.prev = f"{cls.tasks_api_base_url}?page={page-1}&limit={limit}"

        if tasks_count > tasks_skip_count + limit:
            links_data.next = f"{cls.tasks_api_base_url}?page={page+1}&limit={limit}"

        if links_data.prev is not None or links_data.next is not None:
            response.links = links_data
        return response

    @classmethod
    def prepare_task_dto(cls, task: TaskModel) -> TaskDTO:
        task_dict = task.model_dump(mode="json", exclude={"description", "isAcknowledged"})
        if len(task.labels) > 0:
            task_dict["labels"] = [
                LabelDTO(
                    **{
                        "name": label.name,
                        "color": label.color,
                    }
                )
                for label in LabelRepository.list_by_ids(task.labels)
            ]
        task_dict["createdBy"] = cls.prepare_user_dto(task.createdBy)
        if task.assignee is not None:
            task_dict["assignee"] = cls.prepare_user_dto(task.assignee)
        if task.updatedBy is not None:
            task_dict["updatedBy"] = cls.prepare_user_dto(task.updatedBy)
        return TaskDTO(**task_dict)

    @classmethod
    def prepare_user_dto(cls, user_id: str) -> UserDTO:
        UserDTO.model_fields
        return UserDTO(
            **{
                "id": user_id,
                "name": "SYSTEM",
            }
        )
