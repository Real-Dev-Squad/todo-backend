from enum import Enum
from rest_framework import status


class AppHealthStatus(Enum):
    UP = status.HTTP_200_OK
    DOWN = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, http_status):
        self.http_status = http_status


class ComponentHealthStatus(Enum):
    UP = 1
    DOWN = 2
