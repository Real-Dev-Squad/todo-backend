from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from todo.constants.health import AppHealthStatus, ComponentHealthStatus
from django.db import connection
from django.db.utils import OperationalError


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
        # Check PostgreSQL health using Django's connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                is_postgres_healthy = result and result[0] == 1
        except OperationalError:
            is_postgres_healthy = False
        
        postgres_status = ComponentHealthStatus.UP.name if is_postgres_healthy else ComponentHealthStatus.DOWN.name
        
        # Overall health is UP if PostgreSQL is healthy
        overall_healthy = is_postgres_healthy
        overall_status = AppHealthStatus.UP if overall_healthy else AppHealthStatus.DOWN
        
        response = {
            "status": overall_status.name,
            "components": {
                "postgres": {"status": postgres_status},
            },
        }
        return Response(response, overall_status.http_status)
