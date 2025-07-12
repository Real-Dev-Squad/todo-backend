from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from typing import Dict, Any, Callable

from todo.serializers.create_role_serializer import CreateRoleSerializer
from todo.serializers.update_role_serializer import UpdateRoleSerializer
from todo.serializers.get_roles_serializer import RoleQuerySerializer
from todo.services.role_service import RoleService
from todo.exceptions.global_exception_handler import GlobalExceptionHandler
from todo.exceptions.role_exceptions import (
    RoleNotFoundException,
    RoleAlreadyExistsException,
    RoleOperationException,
)


class BaseRoleView(APIView):
    """Base class for role views with common exception handling."""

    def _handle_exceptions(self, func: Callable) -> Response:
        """
        Common exception handling for all role operations.

        Args:
            func: The function to execute with exception handling

        Returns:
            Response: HTTP response with appropriate error handling
        """
        try:
            return func()
        except RoleNotFoundException as e:
            error_response = GlobalExceptionHandler.handle_role_not_found(e)
            return Response({"error": error_response["error"]}, status=error_response["status_code"])
        except RoleAlreadyExistsException as e:
            error_response = GlobalExceptionHandler.handle_role_already_exists(e)
            return Response({"error": error_response["error"]}, status=error_response["status_code"])
        except RoleOperationException as e:
            error_response = GlobalExceptionHandler.handle_role_operation_error(e)
            return Response({"error": error_response["error"]}, status=error_response["status_code"])
        except Exception as e:
            error_response = GlobalExceptionHandler.handle_generic_error(e)
            return Response({"error": error_response["error"]}, status=error_response["status_code"])


class RoleListView(BaseRoleView):
    @classmethod
    def _build_filters(cls, query_serializer: RoleQuerySerializer) -> Dict[str, Any]:
        """
        Build filters dictionary from query parameters.

        Args:
            query_serializer: Validated query serializer

        Returns:
            Dict[str, Any]: Filters dictionary for the service layer
        """
        filters = {}

        if query_serializer.validated_data.get("is_active") is not None:
            filters["is_active"] = query_serializer.validated_data["is_active"]

        if query_serializer.validated_data.get("name"):
            filters["name"] = query_serializer.validated_data["name"]

        if query_serializer.validated_data.get("scope"):
            filters["scope"] = query_serializer.validated_data["scope"]

        return filters

    @extend_schema(
        operation_id="get_roles",
        summary="Get all roles",
        description="Retrieve all roles with optional filtering",
        tags=["roles"],
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by active status",
            ),
            OpenApiParameter(
                name="name",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by role name",
            ),
            OpenApiParameter(
                name="scope",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by role scope (GLOBAL/TEAM)",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Roles retrieved successfully"),
            400: OpenApiResponse(description="Bad request"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        """Get all roles with optional filtering."""

        def _execute():
            query_serializer = RoleQuerySerializer(data=request.query_params)
            query_serializer.is_valid(raise_exception=True)

            filters = self._build_filters(query_serializer)
            role_dtos = RoleService.get_all_roles(filters=filters)
            roles_data = [role_dto.model_dump() for role_dto in role_dtos]

            return Response({"roles": roles_data, "total": len(roles_data)}, status=status.HTTP_200_OK)

        return self._handle_exceptions(_execute)

    @extend_schema(
        operation_id="create_role",
        summary="Create a new role",
        description="Create a new role with the provided details",
        tags=["roles"],
        request=CreateRoleSerializer,
        responses={
            201: OpenApiResponse(description="Role created successfully"),
            400: OpenApiResponse(description="Bad request"),
            409: OpenApiResponse(description="Role already exists"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """Create a new role."""

        def _execute():
            serializer = CreateRoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response({"error": "User authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            role_dto = RoleService.create_role(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description"),
                scope=serializer.validated_data["scope"],
                is_active=serializer.validated_data["is_active"],
                created_by=user_id,
            )

            return Response(
                {"role": role_dto.model_dump(), "message": "Role created successfully"}, status=status.HTTP_201_CREATED
            )

        return self._handle_exceptions(_execute)


class RoleDetailView(BaseRoleView):
    @extend_schema(
        operation_id="get_role_by_id",
        summary="Get role by ID",
        description="Retrieve a single role by its unique identifier",
        tags=["roles"],
        parameters=[
            OpenApiParameter(
                name="role_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the role",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Role retrieved successfully"),
            404: OpenApiResponse(description="Role not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request, role_id: str):
        """Get a single role by ID."""

        def _execute():
            role_dto = RoleService.get_role_by_id(role_id)
            return Response({"role": role_dto.model_dump()}, status=status.HTTP_200_OK)

        return self._handle_exceptions(_execute)

    @extend_schema(
        operation_id="update_role",
        summary="Update role",
        description="Update an existing role with the provided details",
        tags=["roles"],
        parameters=[
            OpenApiParameter(
                name="role_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the role",
            ),
        ],
        request=UpdateRoleSerializer,
        responses={
            200: OpenApiResponse(description="Role updated successfully"),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Role not found"),
            409: OpenApiResponse(description="Role name already exists"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def patch(self, request: Request, role_id: str):
        """Update an existing role."""

        def _execute():
            serializer = UpdateRoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response({"error": "User authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            role_dto = RoleService.update_role(
                role_id=role_id,
                name=serializer.validated_data.get("name"),
                description=serializer.validated_data.get("description"),
                scope=serializer.validated_data.get("scope"),
                is_active=serializer.validated_data.get("is_active"),
                updated_by=user_id,
            )

            return Response(
                {"role": role_dto.model_dump(), "message": "Role updated successfully"}, status=status.HTTP_200_OK
            )

        return self._handle_exceptions(_execute)

    @extend_schema(
        operation_id="delete_role",
        summary="Delete role",
        description="Delete a role by its unique identifier",
        tags=["roles"],
        parameters=[
            OpenApiParameter(
                name="role_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the role to delete",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Role deleted successfully"),
            404: OpenApiResponse(description="Role not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def delete(self, request: Request, role_id: str):
        """Delete a role by ID."""

        def _execute():
            RoleService.delete_role(role_id)
            return Response(status=status.HTTP_204_NO_CONTENT)

        return self._handle_exceptions(_execute)
