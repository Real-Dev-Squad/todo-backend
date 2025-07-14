from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from bson import ObjectId

from todo.middlewares.jwt_auth import get_current_user_info
from todo.serializers.create_task_assignment_serializer import CreateTaskAssignmentSerializer
from todo.services.task_assignment_service import TaskAssignmentService
from todo.dto.task_assignment_dto import CreateTaskAssignmentDTO
from todo.dto.responses.create_task_assignment_response import CreateTaskAssignmentResponse
from todo.dto.responses.error_response import ApiErrorResponse
from todo.constants.messages import ApiErrors
from todo.exceptions.user_exceptions import UserNotFoundException
from todo.exceptions.task_exceptions import TaskNotFoundException


class TaskAssignmentView(APIView):
    @extend_schema(
        operation_id="create_task_assignment",
        summary="Assign task to user or team",
        description="Assign a task to either a user or a team. The system will validate that both the task and assignee exist before creating the assignment.",
        tags=["task-assignments"],
        request=CreateTaskAssignmentSerializer,
        responses={
            201: OpenApiResponse(
                response=CreateTaskAssignmentResponse,
                description="Task assignment created successfully"
            ),
            400: OpenApiResponse(
                response=ApiErrorResponse,
                description="Bad request - validation error or assignee not found"
            ),
            404: OpenApiResponse(
                response=ApiErrorResponse,
                description="Task not found"
            ),
            500: OpenApiResponse(
                response=ApiErrorResponse,
                description="Internal server error"
            ),
        },
    )
    def post(self, request: Request):
        """
        Assign a task to a user or team.
        
        This endpoint allows you to assign a task to either a user or a team.
        The system will validate that:
        - The task exists in the database
        - The assignee (user or team) exists in the database
        - If a task already has an assignment, it will be updated
        
        Args:
            request: HTTP request containing task assignment data
            
        Returns:
            Response: HTTP response with created assignment data or error details
        """
        user = get_current_user_info(request)
        if not user:
            raise AuthenticationFailed(ApiErrors.AUTHENTICATION_FAILED)

        serializer = CreateTaskAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                data={"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dto = CreateTaskAssignmentDTO(**serializer.validated_data)
            response: CreateTaskAssignmentResponse = TaskAssignmentService.create_task_assignment(
                dto, user["user_id"]
            )

            return Response(
                data=response.model_dump(mode="json"),
                status=status.HTTP_201_CREATED
            )

        except TaskNotFoundException as e:
            error_response = ApiErrorResponse(
                statusCode=404,
                message="Task not found",
                errors=[{"detail": str(e)}]
            )
            return Response(
                data=error_response.model_dump(mode="json"),
                status=status.HTTP_404_NOT_FOUND
            )

        except UserNotFoundException as e:
            error_response = ApiErrorResponse(
                statusCode=400,
                message="Assignee not found",
                errors=[{"detail": str(e)}]
            )
            return Response(
                data=error_response.model_dump(mode="json"),
                status=status.HTTP_400_BAD_REQUEST
            )

        except ValueError as e:
            error_response = ApiErrorResponse(
                statusCode=400,
                message="Validation error",
                errors=[{"detail": str(e)}]
            )
            return Response(
                data=error_response.model_dump(mode="json"),
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}]
            )
            return Response(
                data=fallback_response.model_dump(mode="json"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskAssignmentDetailView(APIView):
    @extend_schema(
        operation_id="get_task_assignment",
        summary="Get task assignment by task ID",
        description="Retrieve the assignment details for a specific task",
        tags=["task-assignments"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CreateTaskAssignmentResponse,
                description="Task assignment retrieved successfully"
            ),
            404: OpenApiResponse(
                response=ApiErrorResponse,
                description="Task assignment not found"
            ),
            500: OpenApiResponse(
                response=ApiErrorResponse,
                description="Internal server error"
            ),
        },
    )
    def get(self, request: Request, task_id: str):
        """
        Get task assignment by task ID.
        
        Args:
            request: HTTP request
            task_id: ID of the task to get assignment for
            
        Returns:
            Response: HTTP response with assignment data or error details
        """
        try:
            assignment = TaskAssignmentService.get_task_assignment(task_id)
            if not assignment:
                error_response = ApiErrorResponse(
                    statusCode=404,
                    message="Task assignment not found",
                    errors=[{"detail": f"No assignment found for task {task_id}"}]
                )
                return Response(
                    data=error_response.model_dump(mode="json"),
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                data=assignment.model_dump(mode="json"),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}]
            )
            return Response(
                data=fallback_response.model_dump(mode="json"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        operation_id="delete_task_assignment",
        summary="Delete task assignment",
        description="Remove the assignment for a specific task",
        tags=["task-assignments"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task",
                required=True,
            ),
        ],
        responses={
            204: OpenApiResponse(description="Task assignment deleted successfully"),
            404: OpenApiResponse(
                response=ApiErrorResponse,
                description="Task assignment not found"
            ),
            500: OpenApiResponse(
                response=ApiErrorResponse,
                description="Internal server error"
            ),
        },
    )
    def delete(self, request: Request, task_id: str):
        """
        Delete task assignment by task ID.
        
        Args:
            request: HTTP request
            task_id: ID of the task to delete assignment for
            
        Returns:
            Response: HTTP response with success or error details
        """
        user = get_current_user_info(request)
        if not user:
            raise AuthenticationFailed(ApiErrors.AUTHENTICATION_FAILED)

        try:
            success = TaskAssignmentService.delete_task_assignment(task_id, user["user_id"])
            if not success:
                error_response = ApiErrorResponse(
                    statusCode=404,
                    message="Task assignment not found",
                    errors=[{"detail": f"No assignment found for task {task_id}"}]
                )
                return Response(
                    data=error_response.model_dump(mode="json"),
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}]
            )
            return Response(
                data=fallback_response.model_dump(mode="json"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 