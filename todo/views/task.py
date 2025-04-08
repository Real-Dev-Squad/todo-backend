from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request

from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer
from todo.serializers.create_task_serializer import CreateTaskSerializer
from todo.services.task_service import TaskService
from todo.dto.task_dto import CreateTaskDTO
from todo.dto.responses.create_task_response import CreateTaskResponse


class TaskView(APIView):
    def get(self, request: Request):
        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        response = TaskService.get_tasks(page=query.validated_data["page"], limit=query.validated_data["limit"])

        return Response(data=response.model_dump(mode="json", exclude_none=True), status=status.HTTP_200_OK)

    def post(self, request:Request):
        serializer = CreateTaskSerializer(data=request.data)

        if not serializer.is_valid():
            errors = []
            for field, messages in serializer.errors.items():
                if isinstance(messages, list):
                    for message in messages:
                        errors.append({"field": field, "message": str(message)})
                else:
                    errors.append({"field": field, "message": str(messages)})
            
            return Response(
                {
                    "status": "validation_failed",
                    "statusCode": 400,
                    "errorMessage": "Validation Error",
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dto = CreateTaskDTO(**serializer.validated_data)
            response: CreateTaskResponse = TaskService.create_task(dto)

            return Response(
                data=response.model_dump(mode="json", exclude_none=True), 
                status=status.HTTP_201_CREATED
                )
        
        except Exception as e:
            return Response(
                data={
                    "status": "internal_server_error",
                    "statusCode": 500,
                    "errorMessage": "An unexpected error occurred",
                    "errors": [{"detail": str(e)}],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )