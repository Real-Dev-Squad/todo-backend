from bson import ObjectId
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
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
from todo.dto.responses.error_response import (
    ApiErrorResponse,
    ApiErrorDetail,
    ApiErrorSource,
)
from todo.constants.messages import ApiErrors
from todo.constants.messages import ValidationErrors
from todo.dto.responses.get_tasks_response import GetTasksResponse


class TaskListView(APIView):
    @extend_schema(
        operation_id="get_tasks",
        summary="Get paginated list of tasks",
        description="""
        Retrieve a paginated list of tasks with optional filtering and sorting. Each task now includes an 'in_watchlist' property indicating the watchlist status: true if actively watched, false if in watchlist but inactive, or null if not in watchlist.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        - Example: `Cookie: todo-access=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...`
        
        **Team-based Access Control:**
        - If `teamId` is provided, only shows tasks assigned to that specific team
        - User must be a member of the team to see team tasks
        - Returns 401 if user lacks team membership
        
        **Test with curl:**
        ```bash
        # Get all user tasks
        curl -X GET "http://localhost:8000/v1/tasks?page=1&limit=10" \
             -H "Cookie: todo-access=<your-jwt-token>"
             
        # Get team-specific tasks
        curl -X GET "http://localhost:8000/v1/tasks?teamId=6879287077d79dd472916a3f&page=1&limit=10" \
             -H "Cookie: todo-access=<your-jwt-token>"
        ```
        """,
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of tasks per page (default: 10)",
            ),
            OpenApiParameter(
                name="teamId",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="If provided, filters tasks assigned to this team (e.g., 6879287077d79dd472916a3f).",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=GetTasksResponse,
                description="Tasks retrieved successfully",
                examples=[
                    OpenApiExample(
                        "Tasks Response",
                        summary="Paginated tasks with team assignment",
                        value={
                            "tasks": [
                                {
                                    "id": "6879298277d79dd472916a43",
                                    "title": "Test Task for RBAC Team",
                                    "description": "Testing task creation and team assignment",
                                    "priority": "medium",
                                    "status": "pending",
                                    "assignee_team_id": "6879287077d79dd472916a3f",
                                    "assignee_team_name": "Complete RBAC Test Team",
                                    "created_by": "686a451ad6706973cbd2ba30",
                                    "in_watchlist": None,
                                }
                            ],
                            "pagination": {"page": 1, "limit": 10, "total": 1, "pages": 1},
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Bad request - invalid parameters"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
        },
    )
    def get(self, request: Request):
        """
        Retrieve a paginated list of tasks, or if profile=true, only the current user's tasks.
        """
        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        if query.validated_data["profile"]:
            user = get_current_user_info(request)
            if not user:
                raise AuthenticationFailed(ApiErrors.AUTHENTICATION_FAILED)
            response = TaskService.get_tasks_for_user(
                user_id=user["user_id"],
                page=query.validated_data["page"],
                limit=query.validated_data["limit"],
            )
            return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)

        user = get_current_user_info(request)
        if query.validated_data["profile"]:
            response = TaskService.get_tasks_for_user(
                user_id=user["user_id"],
                page=query.validated_data["page"],
                limit=query.validated_data["limit"],
            )
            return Response(
                data=response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_200_OK,
            )

        team_id = query.validated_data.get("teamId")
        response = TaskService.get_tasks(
            page=query.validated_data["page"],
            limit=query.validated_data["limit"],
            sort_by=query.validated_data["sort_by"],
            order=query.validated_data.get("order"),
            user_id=user["user_id"],
            team_id=team_id,
        )
        return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="create_task",
        summary="Create new task",
        description="""
        Create task with privacy controls and team assignment.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Team Assignment:**
        - If `assignee_team_id` is provided, task is assigned to that team
        - User must be a member of the team to assign tasks to it
        - Team members with appropriate roles can view and manage team tasks
        
        **Privacy Controls:**
        - Tasks can be marked as private or public
        - Private tasks are only visible to creator and assigned team members
        
        **Test with curl:**
        ```bash
        # Create task assigned to team
        curl -X POST "http://localhost:8000/v1/tasks" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{
               "title": "My Test Task",
               "description": "Testing task creation via Swagger",
               "priority": "high",
               "assignee_team_id": "6879287077d79dd472916a3f"
             }'
             
        # Create personal task (no team assignment)
        curl -X POST "http://localhost:8000/v1/tasks" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{
               "title": "Personal Task",
               "description": "My personal task",
               "priority": "medium"
             }'
        ```
        """,
        tags=["tasks"],
        request=CreateTaskSerializer,
        responses={
            201: OpenApiResponse(
                response=CreateTaskResponse,
                description="Task created successfully",
                examples=[
                    OpenApiExample(
                        "Task Created Successfully",
                        summary="Task assigned to team",
                        value={
                            "task": {
                                "id": "6879298277d79dd472916a43",
                                "title": "My Test Task",
                                "description": "Testing task creation via Swagger",
                                "priority": "high",
                                "status": "pending",
                                "assignee_team_id": "6879287077d79dd472916a3f",
                                "assignee_team_name": "Complete RBAC Test Team",
                                "created_by": "686a451ad6706973cbd2ba30",
                                "is_private": False,
                            },
                            "message": "Task created successfully",
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Validation error - invalid team ID or missing required fields"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Permission denied - not a member of assigned team",
                examples=[
                    OpenApiExample(
                        "Team Membership Required",
                        value={
                            "error": "Team membership required",
                            "message": "Must be a member of team to assign tasks",
                            "details": {"team_id": "6879287077d79dd472916a3f"},
                        },
                    )
                ],
            ),
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
                return Response(
                    data=error_response.model_dump(mode="json"),
                    status=error_response.statusCode,
                )

            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": (str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR)}],
            )
            return Response(
                data=fallback_response.model_dump(mode="json"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                        source={ApiErrorSource.PARAMETER: field},
                        title=ApiErrors.VALIDATION_ERROR,
                        detail=str(messages),
                    )
                )

        error_response = ApiErrorResponse(statusCode=400, message=ApiErrors.VALIDATION_ERROR, errors=formatted_errors)

        return Response(
            data=error_response.model_dump(mode="json"),
            status=status.HTTP_400_BAD_REQUEST,
        )


class TaskDetailView(APIView):
    @extend_schema(
        operation_id="get_task_by_id",
        summary="Get task by ID",
        description="""
        Retrieve a single task by its unique identifier.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Access Control:**
        - Task creator can always view their tasks
        - Team members can view tasks assigned to their team
        - Private tasks are only visible to creator and team members
        - Returns 403 if user lacks permission to view task
        
        **Test with curl:**
        ```bash
        curl -X GET "http://localhost:8000/v1/tasks/6879298277d79dd472916a43" \
             -H "Cookie: todo-access=<your-jwt-token>"
        ```
        """,
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task (e.g., 6879298277d79dd472916a43)",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=GetTaskByIdResponse,
                description="Task retrieved successfully",
                examples=[
                    OpenApiExample(
                        "Task Details Response",
                        summary="Task with team assignment",
                        value={
                            "data": {
                                "id": "6879298277d79dd472916a43",
                                "title": "Test Task for RBAC Team",
                                "description": "Testing task creation and team assignment",
                                "priority": "high",
                                "status": "pending",
                                "assignee_team_id": "6879287077d79dd472916a3f",
                                "assignee_team_name": "Complete RBAC Test Team",
                                "created_by": "686a451ad6706973cbd2ba30",
                                "created_at": "2024-01-15T10:30:00Z",
                                "updated_at": "2024-01-15T10:30:00Z",
                                "is_private": False,
                                "in_watchlist": None,
                            }
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Permission denied - insufficient access to task",
                examples=[
                    OpenApiExample(
                        "Task Access Denied",
                        value={
                            "error": "Permission denied",
                            "message": "Insufficient permissions to view this task",
                            "details": {"task_id": "6879298277d79dd472916a43", "reason": "not_team_member"},
                        },
                    )
                ],
            ),
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
        description="""
        Delete a task by its unique identifier.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Permission Requirements:**
        - Task creator can delete their own tasks
        - Team admins/owners can delete team tasks
        - Members cannot delete team tasks (unless they created them)
        
        **Test with curl:**
        ```bash
        curl -X DELETE "http://localhost:8000/v1/tasks/6879298277d79dd472916a43" \
             -H "Cookie: todo-access=<your-jwt-token>"
        ```
        
        **Expected Response:** HTTP 204 No Content
        """,
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task to delete (e.g., 6879298277d79dd472916a43)",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Task deleted successfully"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Permission denied - insufficient role to delete task",
                examples=[
                    OpenApiExample(
                        "Task Deletion Denied",
                        value={
                            "error": "Permission denied",
                            "message": "Insufficient permissions to delete this task",
                            "details": {"task_id": "6879298277d79dd472916a43", "required_role": "admin"},
                        },
                    )
                ],
            ),
            404: OpenApiResponse(description="Task not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def delete(self, request: Request, task_id: str):
        user = get_current_user_info(request)
        task_id = ObjectId(task_id)
        TaskService.delete_task(task_id, user["user_id"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="update_task",
        summary="Update or defer task",
        description="""
        Partially update a task or defer it based on the action parameter.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Permission Requirements:**
        - Task creator can update their own tasks
        - Team admins/owners can update team tasks
        - Members can update team tasks they have access to
        
        **Actions:**
        - `update`: Modify task fields (title, description, priority, status, etc.)
        - `defer`: Postpone task execution to a specific date
        
        **Updateable Fields:**
        - title, description, priority, status
        - assignee_team_id (reassign to different team)
        - is_private (change privacy setting)
        
        **Test with curl:**
        ```bash
        # Update task details
        curl -X PATCH "http://localhost:8000/v1/tasks/6879298277d79dd472916a43?action=update" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{
               "title": "Updated Task Title",
               "priority": "urgent",
               "status": "in_progress"
             }'
             
        # Defer task
        curl -X PATCH "http://localhost:8000/v1/tasks/6879298277d79dd472916a43?action=defer" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{"deferredTill": "2024-02-01T10:00:00Z"}'
        ```
        """,
        tags=["tasks"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task (e.g., 6879298277d79dd472916a43)",
            ),
            OpenApiParameter(
                name="action",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Action to perform: 'update' (default) or 'defer'",
                enum=["update", "defer"],
            ),
        ],
        request=UpdateTaskSerializer,
        responses={
            200: OpenApiResponse(
                description="Task updated successfully",
                examples=[
                    OpenApiExample(
                        "Task Updated Successfully",
                        summary="Updated task details",
                        value={
                            "id": "6879298277d79dd472916a43",
                            "title": "Updated Task Title",
                            "description": "Testing task creation and team assignment",
                            "priority": "urgent",
                            "status": "in_progress",
                            "assignee_team_id": "6879287077d79dd472916a3f",
                            "assignee_team_name": "Complete RBAC Test Team",
                            "updated_at": "2024-01-15T11:30:00Z",
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Bad request - invalid action or validation error"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Permission denied - insufficient role to update task",
                examples=[
                    OpenApiExample(
                        "Task Update Denied",
                        value={
                            "error": "Permission denied",
                            "message": "Insufficient permissions to update this task",
                            "details": {"task_id": "6879298277d79dd472916a43", "user_role": "member"},
                        },
                    )
                ],
            ),
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
                task_id=task_id,
                validated_data=serializer.validated_data,
                user_id=user["user_id"],
            )
        else:
            raise ValidationError({"action": ValidationErrors.UNSUPPORTED_ACTION.format(action)})

        return Response(data=updated_task_dto.model_dump(mode="json"), status=status.HTTP_200_OK)
