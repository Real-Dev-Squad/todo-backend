from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer
from todo.services.task_service import TaskService


class TaskView(APIView):
    def get(self, request: Request):
        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page = query.validated_data["page"]
        limit = query.validated_data["limit"]
        response = TaskService.get_tasks(page, limit)
        return Response(response.model_dump(mode="json", exclude_none=True), status.HTTP_200_OK)
