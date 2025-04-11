from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from django.conf import settings

from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer
from todo.serializers.create_task_serializer import CreateTaskSerializer
from todo.services.task_service import TaskService
from todo.dto.task_dto import CreateTaskDTO
from todo.dto.responses.create_task_response import CreateTaskResponse


class TaskView(APIView):
    def get(self, request: Request):
        """
        Retrieve a paginated list of tasks.
        """
        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        response = TaskService.get_tasks(page=query.validated_data["page"], limit=query.validated_data["limit"])

        return Response(data=response.model_dump(mode="json", exclude_none=True), status=status.HTTP_200_OK)

    def post(self, request:Request):
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

            return Response(
                data=response.model_dump(mode="json"), 
                status=status.HTTP_201_CREATED
                )
        
        except Exception as e:
            return Response(
                data={
                    "status": "internal_server_error",
                    "statusCode": 500,
                    "errorMessage": "An unexpected error occurred",
                    "errors": [{"detail": str(e)}] if settings.DEBUG else [{"detail": "Internal server error"}],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_validation_errors(self, errors):
        formatted_errors = []
        for field, messages in errors.items():
            if isinstance(messages, list):
                for message in messages:
                    formatted_errors.append({"field": field, "message": str(message)})
            else:
                formatted_errors.append({"field": field, "message": str(messages)})
        
        return Response(
                {
                    "status": "validation_failed",
                    "statusCode": 400,
                    "errorMessage": "Validation Error",
                    "errors": formatted_errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )