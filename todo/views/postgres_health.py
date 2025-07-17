from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from todo.constants.health import AppHealthStatus, ComponentHealthStatus
from todo_project.db.postgres_config import PostgreSQLDatabaseManager


class PostgresHealthView(APIView):
    @extend_schema(
        operation_id="postgres_health_check",
        summary="Check PostgreSQL health",
        description="Returns 200 if PostgreSQL is healthy, 503 if not.",
        tags=["health", "postgres"],
        responses={
            200: OpenApiResponse(description="PostgreSQL is healthy"),
            503: OpenApiResponse(description="PostgreSQL health check failed"),
        },
    )
    def get(self, request):
        pg_manager = PostgreSQLDatabaseManager()
        is_db_healthy = pg_manager.check_database_health()
        db_status = ComponentHealthStatus.UP.name if is_db_healthy else ComponentHealthStatus.DOWN.name
        overall_status = AppHealthStatus.UP if is_db_healthy else AppHealthStatus.DOWN
        response = {
            "status": overall_status.name,
            "components": {
                "postgres": {"status": db_status},
            },
        }
        return Response(response, overall_status.http_status)
