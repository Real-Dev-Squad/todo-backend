from rest_framework.views import APIView
from rest_framework.response import Response
from todo.constants.health import AppHealthStatus, ComponentHealthStatus
from todo_project.db.config import DatabaseManager

database_manager = DatabaseManager()


class HealthView(APIView):
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
