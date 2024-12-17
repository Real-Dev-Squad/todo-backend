from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request


class TaskView(APIView):
    def get(self, request: Request):
        return Response({}, status.HTTP_200_OK)
