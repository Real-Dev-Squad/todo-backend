from bson import ObjectId
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.middlewares.jwt_auth import get_current_user_info
from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer
from todo.serializers.create_task_serializer import CreateTaskSerializer
from todo.serializers.update_task_serializer import UpdateTaskSerializer
from todo.serializers.defer_task_serializer import DeferTaskSerializer
from todo.services.task_service import TaskService
from todo.dto.task_dto import CreateTaskDTO
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.dto.responses.get_task_by_id_response import GetTaskByIdResponse
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.constants.messages import ApiErrors
from todo.constants.messages import ValidationErrors


class TaskListView(APIView):
    @extend_schema(
        operation_id="get_tasks",
        summary="Get paginated list of tasks",
        description="Retrieve a paginated list of tasks with optional filtering and sorting",
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of tasks per page",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Successful response"),
            400: OpenApiResponse(description="Bad request"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        """
        Retrieve a paginated list of tasks.
        """
        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        response = TaskService.get_tasks(page=query.validated_data["page"], limit=query.validated_data["limit"])
        return Response(data=response.model_dump(mode="json", exclude_none=True), status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="create_task",
        summary="Create a new task",
        description="Create a new task with the provided details",
        tags=["tasks"],
        request=CreateTaskSerializer,
        responses={
            201: OpenApiResponse(description="Task created successfully"),
            400: OpenApiResponse(description="Bad request"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """
        Create a new task.

        Args:
            request: HTTP request containing task data

        Returns:
            Response: HTTP response with created task data or error details
        """
        user = get_current_user_info(request)

        serializer = CreateTaskSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        try:
            dto = CreateTaskDTO(**serializer.validated_data, createdBy=user["user_id"])
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


class TaskDetailView(APIView):
    @extend_schema(
        operation_id="get_task_by_id",
        summary="Get task by ID",
        description="Retrieve a single task by its unique identifier",
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Task retrieved successfully"),
            404: OpenApiResponse(description="Task not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request, task_id: str):
        """
        Retrieve a single task by ID.
        """
        task_dto = TaskService.get_task_by_id(task_id)
        response_data = GetTaskByIdResponse(data=task_dto)
        return Response(data=response_data.model_dump(mode="json"), status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="delete_task",
        summary="Delete task",
        description="Delete a task by its unique identifier",
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task to delete",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Task deleted successfully"),
            404: OpenApiResponse(description="Task not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def delete(self, request: Request, task_id: str):
        """
        Delete a task by ID.

        .. deprecated:: 1.0.0
            This endpoint is deprecated and will be removed in a future version.
            Consider using the PATCH endpoint with action=delete instead.
        """
        user = get_current_user_info(request)

        task_id = ObjectId(task_id)
        TaskService.delete_task(task_id, user["user_id"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="update_task",
        summary="Update or defer task",
        description="Partially update a task or defer it based on the action parameter",
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task",
            ),
            OpenApiParameter(
                name="action",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Action to perform: 'update' or 'defer'",
            ),
        ],
        request=UpdateTaskSerializer,
        responses={
            200: OpenApiResponse(description="Task updated successfully"),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Task not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def patch(self, request: Request, task_id: str):
        """
        Partially updates a task by its ID.
        Can also be used to defer a task by using ?action=defer query parameter.
        """
        action = request.query_params.get("action", "update")
        user = get_current_user_info(request)

        if action == "defer":
            serializer = DeferTaskSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            updated_task_dto = TaskService.defer_task(
                task_id=task_id,
                deferred_till=serializer.validated_data["deferredTill"],
                user_id=user["user_id"],
            )
        elif action == "update":
            serializer = UpdateTaskSerializer(data=request.data, partial=True)

            serializer.is_valid(raise_exception=True)

            updated_task_dto = TaskService.update_task(
                task_id=task_id, validated_data=serializer.validated_data, user_id=user["user_id"]
            )
        else:
            raise ValidationError({"action": ValidationErrors.UNSUPPORTED_ACTION.format(action)})

        return Response(data=updated_task_dto.model_dump(mode="json", exclude_none=True), status=status.HTTP_200_OK)
