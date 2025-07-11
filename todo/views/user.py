from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.services.user_service import UserService
from todo.dto.user_dto import UserSearchDTO, UserSearchResponseDTO, UserDTO
from todo.dto.responses.error_response import ApiErrorResponse
from todo.middlewares.jwt_auth import get_current_user_info
from rest_framework.exceptions import AuthenticationFailed
from todo.constants.messages import ApiErrors


class UsersView(APIView):
    @extend_schema(
        operation_id="get_user_profile",
        summary="Get user profile",
        description="Get user profile details",
        tags=["users"],
        responses={200: UserDTO, 401: ApiErrorResponse},
    )
    def get(self, request: Request):
        profile = request.query_params.get("profile")
        if profile == "true":
            user_info = get_current_user_info(request)
            if not user_info:
                raise AuthenticationFailed(ApiErrors.AUTHENTICATION_FAILED)
            return Response(
                {"statusCode": 200, "message": "Current user details fetched successfully", "data": user_info},
                status=200,
            )
        return Response({"statusCode": 404, "message": "Route does not exist.", "data": None}, status=404)


class UserSearchView(APIView):
    @extend_schema(
        operation_id="search_users",
        summary="Search users with fuzzy search",
        description="Search users by name or email using fuzzy search with MongoDB regex capabilities. "
        "Supports case-insensitive search across both name and email fields.",
        tags=["users"],
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search query for name or email (fuzzy search)",
                required=False,
            ),
            OpenApiParameter(
                name="name",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by name only",
                required=False,
            ),
            OpenApiParameter(
                name="email",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by email only",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of results per page (default: 10, max: 100)",
                required=False,
            ),
        ],
        responses={
            200: UserSearchResponseDTO,
            400: OpenApiResponse(description="Bad request - invalid parameters"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        """
        Search users with various search options:
        - q: General search across name and email
        - name: Search by name only
        - email: Search by email only
        - If no search parameters provided, returns all users with pagination
        """
        try:
            # Get query parameters
            query = request.query_params.get("q", "").strip()
            name = request.query_params.get("name", "").strip()
            email = request.query_params.get("email", "").strip()
            page = int(request.query_params.get("page", 1))
            limit = int(request.query_params.get("limit", 10))

            # Determine search type and execute
            if query:
                # General search across name and email
                users, total_count = UserService.search_users(query, page, limit)
            elif name:
                # Search by name only
                users, total_count = UserService.search_users_by_name(name, page, limit)
            elif email:
                # Search by email only
                users, total_count = UserService.search_users_by_email(email, page, limit)
            else:
                # Get all users with pagination
                users, total_count = UserService.get_all_users(page, limit)

            # Convert to DTOs
            user_dtos = [
                UserSearchDTO(
                    id=str(user.id),
                    name=user.name,
                    email_id=user.email_id,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
                for user in users
            ]

            response_data = UserSearchResponseDTO(
                users=user_dtos,
                total_count=total_count,
                page=page,
                limit=limit,
            )

            return Response(
                {
                    "statusCode": status.HTTP_200_OK,
                    "message": "Users searched successfully",
                    "data": response_data.model_dump(),
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            return Response(
                {
                    "statusCode": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid parameters",
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Internal server error",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
