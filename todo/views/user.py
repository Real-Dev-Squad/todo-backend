from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from todo.constants.messages import ApiErrors
from todo.services.user_service import UserService
from todo.repositories.user_repository import UserRepository
from todo.services.cloudinary_service import CloudinaryService
from todo.exceptions.auth_exceptions import APIException
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.dto.user_dto import UserSearchResponseDTO, UsersDTO
from todo.dto.responses.error_response import ApiErrorResponse
from drf_spectacular.utils import OpenApiExample, inline_serializer
from rest_framework import serializers
from todo.serializers.update_profile_serializer import UpdateProfileSerializer
import logging


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
            200: UserSearchResponseDTO,
            204: OpenApiResponse(description="No users found"),
            401: ApiErrorResponse,
            400: OpenApiResponse(description="Bad request - invalid parameters"),
            404: OpenApiResponse(description="Route does not exist"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        profile = request.query_params.get("profile")
        if profile == "true":
            userData = UserService.get_user_by_id(request.user_id)
            if not userData:
                return Response(
                    {
                        "statusCode": 404,
                        "message": ApiErrors.USER_NOT_FOUND,
                        "data": None,
                    },
                    status=404,
                )
            userData = userData.model_dump(mode="json", exclude_none=True)
            userResponse = {
                "id": userData["id"],
                "email": userData["email_id"],
                "name": userData.get("name"),
                "picture": userData.get("picture"),
            }
            return Response(
                {
                    "message": "Current user details fetched successfully",
                    "data": userResponse,
                },
                status=200,
            )

        # Handle search functionality
        search = request.query_params.get("search", "").strip()
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        # If no search parameter provided, return 404
        if search:
            users, total_count = UserService.search_users(search, page, limit)
        else:
            users, total_count = UserService.get_all_users(page, limit)

        user_dtos = [
            UsersDTO(
                id=str(user.id),
                name=user.name,
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
                "message": "Users fetched successfully",
                "data": response_data.model_dump(),
            },
            status=status.HTTP_200_OK,
        )


class UserDetailView(APIView):
    @extend_schema(
        operation_id="update_user_profile",
        summary="Update current user profile picture",
        description="Updates the profile picture of the currently authenticated user.",
        tags=["users"],
        request=inline_serializer(
            name="UserProfilePictureRequest",
            fields={
                "picture": serializers.FileField(),
            },
        ),
        responses={
            200: OpenApiResponse(description="Profile picture updated"),
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Unauthorized"),
            500: OpenApiResponse(description="Internal server error"),
        },
        examples=[
            OpenApiExample(
                name="Update profile image",
                value={"picture": "<binary file>"},
                request_only=True,
            )
        ],
    )
    def patch(self, request: Request):
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        picture_file = serializer.validated_data["picture"]

        try:
            profile_url = CloudinaryService.upload_image(
                file_data=picture_file.read(),
                user_id=request.user_id,
                image_name="profile-picture",
            )
        except APIException:
            return Response(
                {"message": "Image upload configuration error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to upload image for user {request.user_id}: {str(e)}")
            return Response(
                {"message": "Failed to upload image"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user = UserRepository.update_picture_by_id(request.user_id, profile_url)
        userData = user.model_dump(mode="json", exclude_none=True)
        userResponse = {
            "id": userData["id"],
            "email": userData["email_id"],
            "name": userData.get("name"),
            "picture": userData.get("picture"),
        }
        return Response({"message": "User updated successfully", "data": userResponse}, status=200)
