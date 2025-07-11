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
        operation_id="get_users",
        summary="Get users with search and pagination",
        description="Get user profile details or search users with fuzzy search. "
        "Use 'profile=true' to get current user details, or use search parameter to find users.",
        tags=["users"],
        parameters=[
            OpenApiParameter(
                name="profile",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Set to 'true' to get current user profile",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search query for name or email (fuzzy search)",
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
            200: UserDTO,
            200: UserSearchResponseDTO,
            401: ApiErrorResponse,
            400: OpenApiResponse(description="Bad request - invalid parameters"),
            404: OpenApiResponse(description="Route does not exist"),
            500: OpenApiResponse(description="Internal server error"),
        },
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

        # Handle search functionality
        search = request.query_params.get("search", "").strip()
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        # If no search parameter provided, return 404
        if not search:
            return Response({"statusCode": 404, "message": "Route does not exist.", "data": None}, status=404)

        try:
            users, total_count = UserService.search_users(search, page, limit)

            # Return 204 if no users found
            if not users:
                return Response(
                    {
                        "statusCode": status.HTTP_204_NO_CONTENT,
                        "message": "No users found",
                        "data": None,
                    },
                    status=status.HTTP_204_NO_CONTENT,
                )

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
