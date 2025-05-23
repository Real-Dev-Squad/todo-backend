from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from django.conf import settings

from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer
from todo.serializers.create_task_serializer import CreateTaskSerializer
from todo.services.task_service import TaskService
from todo.dto.task_dto import CreateTaskDTO
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.dto.responses.get_task_by_id_response import GetTaskByIdResponse
from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.constants.messages import ApiErrors


class TaskView(APIView):
    def get(self, request: Request, task_id: str | None = None):
        """
        Retrieve a paginated list of tasks or a single task by ID.
        """
        if task_id:
            try:
                task_dto = TaskService.get_task_by_id(task_id)
                response_data = GetTaskByIdResponse(data=task_dto)
                return Response(data=response_data.model_dump(mode="json"), status=status.HTTP_200_OK)
            except TaskNotFoundException as e:
                error_response = ApiErrorResponse(
                    statusCode=status.HTTP_404_NOT_FOUND,
                    message=ApiErrors.TASK_NOT_FOUND_TITLE,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PATH: "task_id"},
                            title=ApiErrors.TASK_NOT_FOUND_TITLE,
                            detail=str(e),
                        )
                    ],
                )
                return Response(
                    data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_404_NOT_FOUND
                )
            except ValueError as e:
                error_response = ApiErrorResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message=ApiErrors.INVALID_TASK_ID_FORMAT,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PATH: "task_id"},
                            title=ApiErrors.VALIDATION_ERROR,
                            detail=str(e),
                        )
                    ],
                )
                return Response(
                    data=error_response.model_dump(mode="json", exclude_none=True), status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                fallback_response = ApiErrorResponse(
                    statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                    errors=[ApiErrorDetail(detail=str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR)],
                )
                return Response(
                    data=fallback_response.model_dump(mode="json", exclude_none=True),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        response = TaskService.get_tasks(page=query.validated_data["page"], limit=query.validated_data["limit"])

        return Response(data=response.model_dump(mode="json", exclude_none=True), status=status.HTTP_200_OK)

    def post(self, request: Request):
        """
        Create a new task.

        Args:
            request: HTTP request containing task data

        Returns:
            Response: HTTP response with created task data or error details
        """
        serializer = CreateTaskSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        try:
            dto = CreateTaskDTO(**serializer.validated_data)
            response: CreateTaskResponse = TaskService.create_task(dto)

            return Response(data=response.model_dump(mode="json"), status=status.HTTP_201_CREATED)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                error_response = e.args[0]
                return Response(data=error_response.model_dump(mode="json"), status=error_response.statusCode)

            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}],
            )
            return Response(
                data=fallback_response.model_dump(mode="json"), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _handle_validation_errors(self, errors):
        formatted_errors = []
        for field, messages in errors.items():
            if isinstance(messages, list):
                for message in messages:
                    formatted_errors.append(
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: field},
                            title=ApiErrors.VALIDATION_ERROR,
                            detail=str(message),
                        )
                    )
            else:
                formatted_errors.append(
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: field}, title=ApiErrors.VALIDATION_ERROR, detail=str(messages)
                    )
                )

        error_response = ApiErrorResponse(statusCode=400, message=ApiErrors.VALIDATION_ERROR, errors=formatted_errors)

        return Response(data=error_response.model_dump(mode="json"), status=status.HTTP_400_BAD_REQUEST)
