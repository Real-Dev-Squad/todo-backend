from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer


class TaskView(APIView):
    def get(self, request: Request):
        query = GetTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response({}, status.HTTP_200_OK)
