from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from todo.serializers.create_role_serializer import CreateRoleSerializer
from todo.serializers.update_role_serializer import UpdateRoleSerializer
from todo.serializers.get_roles_serializer import RoleQuerySerializer
from todo.services.role_service import RoleService
from todo.exceptions.role_exceptions import RoleNotFoundException, RoleAlreadyExistsException


class RoleListView(APIView):
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
                name="type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by role type",
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
        try:
            query_serializer = RoleQuerySerializer(data=request.query_params)
            query_serializer.is_valid(raise_exception=True)

            filters = {}
            if query_serializer.validated_data.get("is_active") is not None:
                filters["is_active"] = query_serializer.validated_data["is_active"]
            if query_serializer.validated_data.get("type"):
                filters["type"] = query_serializer.validated_data["type"]
            if query_serializer.validated_data.get("scope"):
                filters["scope"] = query_serializer.validated_data["scope"]

            role_dtos = RoleService.get_all_roles(filters=filters)
            roles_data = [role_dto.model_dump() for role_dto in role_dtos]

            return Response({"roles": roles_data, "total": len(roles_data)}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e) if settings.DEBUG else "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        try:
            serializer = CreateRoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response({"error": "User authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            role_dto = RoleService.create_role(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description"),
                role_type=serializer.validated_data["type"],
                scope=serializer.validated_data["scope"],
                is_active=serializer.validated_data["is_active"],
                created_by=user_id,
            )

            return Response(
                {"role": role_dto.model_dump(), "message": "Role created successfully"}, status=status.HTTP_201_CREATED
            )

        except RoleAlreadyExistsException as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        except Exception as e:
            return Response(
                {"error": str(e) if settings.DEBUG else "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RoleDetailView(APIView):
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
        try:
            role_dto = RoleService.get_role_by_id(role_id)
            return Response({"role": role_dto.model_dump()}, status=status.HTTP_200_OK)

        except RoleNotFoundException as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response(
                {"error": str(e) if settings.DEBUG else "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        try:
            serializer = UpdateRoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response({"error": "User authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            role_dto = RoleService.update_role(
                role_id=role_id,
                name=serializer.validated_data.get("name"),
                description=serializer.validated_data.get("description"),
                type=serializer.validated_data.get("type"),
                scope=serializer.validated_data.get("scope"),
                is_active=serializer.validated_data.get("is_active"),
                updated_by=user_id,
            )

            return Response(
                {"role": role_dto.model_dump(), "message": "Role updated successfully"}, status=status.HTTP_200_OK
            )

        except RoleNotFoundException as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        except RoleAlreadyExistsException as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        except Exception as e:
            return Response(
                {"error": str(e) if settings.DEBUG else "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        try:
            RoleService.delete_role(role_id)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except RoleNotFoundException as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response(
                {"error": str(e) if settings.DEBUG else "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
