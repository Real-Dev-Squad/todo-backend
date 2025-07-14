from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from todo.constants.health import AppHealthStatus, ComponentHealthStatus
from todo_project.db.config import DatabaseManager
from todo_project.db.postgres_config import PostgreSQLDatabaseManager

database_manager = DatabaseManager()
postgres_manager = PostgreSQLDatabaseManager()


class HealthView(APIView):
    @extend_schema(
        operation_id="health_check",
        summary="Health check",
        description="Check the health status of the application and its components",
        tags=["health"],
        responses={
            200: OpenApiResponse(description="Application is healthy"),
            503: OpenApiResponse(description="Application is unhealthy"),
        },
    )
    def get(self, request):
        global database_manager, postgres_manager
        
        # Check MongoDB health
        is_mongo_healthy = database_manager.check_database_health()
        mongo_status = ComponentHealthStatus.UP.name if is_mongo_healthy else ComponentHealthStatus.DOWN.name
        
        # Check PostgreSQL health
        is_postgres_healthy = postgres_manager.check_database_health()
        postgres_status = ComponentHealthStatus.UP.name if is_postgres_healthy else ComponentHealthStatus.DOWN.name
        
        # Overall health is UP if both databases are healthy
        # For now, we'll consider the app healthy if either database is healthy during migration
        overall_healthy = is_mongo_healthy or is_postgres_healthy
        overall_status = AppHealthStatus.UP if overall_healthy else AppHealthStatus.DOWN
        
        response = {
            "status": overall_status.name,
            "components": {
                "mongodb": {"status": mongo_status},
                "postgres": {"status": postgres_status},
            },
        }
        return Response(response, overall_status.http_status)
