from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from todo.constants.health import AppHealthStatus, ComponentHealthStatus
from todo_project.db.config import DatabaseManager

database_manager = DatabaseManager()


class HealthView(APIView):
    @extend_schema(
        operation_id="health_check",
        summary="Health check",
        description="Check the health status of the application and its components",
        tags=["health"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["UP", "DOWN"]},
                    "components": {
                        "type": "object",
                        "properties": {
                            "db": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string", "enum": ["UP", "DOWN"]},
                                },
                            },
                        },
                    },
                },
            },
            503: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["UP", "DOWN"]},
                    "components": {
                        "type": "object",
                        "properties": {
                            "db": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string", "enum": ["UP", "DOWN"]},
                                },
                            },
                        },
                    },
                },
            },
        },
        examples=[
            {
                "name": "Healthy Application",
                "summary": "Application is healthy",
                "value": {
                    "status": "UP",
                    "components": {
                        "db": {"status": "UP"},
                    },
                },
                "response_only": True,
                "status_codes": ["200"],
            },
            {
                "name": "Unhealthy Application",
                "summary": "Application is unhealthy",
                "value": {
                    "status": "DOWN",
                    "components": {
                        "db": {"status": "DOWN"},
                    },
                },
                "response_only": True,
                "status_codes": ["503"],
            },
        ],
    )
    def get(self, request):
        global database_manager
        is_db_healthy = database_manager.check_database_health()
        db_status = ComponentHealthStatus.UP.name if is_db_healthy else ComponentHealthStatus.DOWN.name
        overall_status = AppHealthStatus.UP if is_db_healthy else AppHealthStatus.DOWN
        response = {
            "status": overall_status.name,
            "components": {
                "db": {"status": db_status},
            },
        }
        return Response(response, overall_status.http_status)
