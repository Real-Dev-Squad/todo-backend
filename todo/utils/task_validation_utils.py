from todo.repositories.task_repository import TaskRepository
from todo.models.task import TaskModel
from todo.constants.messages import ApiErrors
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource


def validate_task_exists(task_id: str) -> TaskModel:
    """
    Common function to validate if a task exists in the task collection.

    Args:
        task_id (str): The task ID to validate

    Returns:
        TaskModel: The task model if found

    Raises:
        ValueError: If task doesn't exist, with ApiErrorResponse
    """
    task = TaskRepository.get_by_id(task_id)
    if not task:
        raise ValueError(
            ApiErrorResponse(
                statusCode=404,
                message=ApiErrors.TASK_NOT_FOUND.format(task_id),
                errors=[
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: "taskId"},
                        title=ApiErrors.TASK_NOT_FOUND_TITLE,
                        detail=ApiErrors.TASK_NOT_FOUND.format(task_id),
                    )
                ],
            )
        )

    return task
