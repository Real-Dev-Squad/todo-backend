from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from django.conf import settings

from todo.serializers.create_team_serializer import CreateTeamSerializer
from todo.services.team_service import TeamService
from todo.dto.team_dto import CreateTeamDTO
from todo.dto.responses.create_team_response import CreateTeamResponse
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.constants.messages import ApiErrors
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.dto.team_dto import TeamDTO
from todo.services.user_service import UserService


class TeamListView(APIView):
    def get(self, request: Request):
        """
        Get all teams assigned to the authenticated user.
        """
        try:
            user_id = request.user_id
            response: GetUserTeamsResponse = TeamService.get_user_teams(user_id)

            return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                error_response = e.args[0]
                return Response(data=error_response.model_dump(mode="json"), status=error_response.statusCode)

            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}],
            )
            return Response(
                data=fallback_response.model_dump(mode="json"), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request: Request):
        """
        Create a new team.
        """
        serializer = CreateTeamSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        try:
            dto = CreateTeamDTO(**serializer.validated_data)
            created_by_user_id = request.user_id
            response: CreateTeamResponse = TeamService.create_team(dto, created_by_user_id)

            return Response(data=response.model_dump(mode="json"), status=status.HTTP_201_CREATED)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                error_response = e.args[0]
                return Response(data=error_response.model_dump(mode="json"), status=error_response.statusCode)

            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}],
            )
            return Response(
                data=fallback_response.model_dump(mode="json"), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _handle_validation_errors(self, errors):
        formatted_errors = []
        for field, messages in errors.items():
            if isinstance(messages, list):
                for message in messages:
                    formatted_errors.append(
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: field},
                            title=ApiErrors.VALIDATION_ERROR,
                            detail=str(message),
                        )
                    )
            else:
                formatted_errors.append(
                    ApiErrorDetail(
                        source={ApiErrorSource.PARAMETER: field}, title=ApiErrors.VALIDATION_ERROR, detail=str(messages)
                    )
                )

        error_response = ApiErrorResponse(statusCode=400, message=ApiErrors.VALIDATION_ERROR, errors=formatted_errors)

        return Response(data=error_response.model_dump(mode="json"), status=status.HTTP_400_BAD_REQUEST)


class TeamDetailView(APIView):
    @extend_schema(
        operation_id="get_team_by_id",
        summary="Get team by ID",
        description="Retrieve a single team by its unique identifier. Optionally, set ?member=true to get users belonging to this team.",
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
            ),
            OpenApiParameter(
                name="member",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="If true, returns users that belong to this team instead of team details.",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Team or team members retrieved successfully"),
            404: OpenApiResponse(description="Team not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request, team_id: str):
        """
        Retrieve a single team by ID, or users in the team if ?member=true.
        """
        try:
            member = request.query_params.get("member", "false").lower() == "true"
            if member:
                from todo.repositories.team_repository import UserTeamDetailsRepository

                user_ids = UserTeamDetailsRepository.get_users_by_team_id(team_id)
                users = UserService.get_users_by_ids(user_ids)
                return Response(data=[user.model_dump(mode="json") for user in users], status=status.HTTP_200_OK)
            else:
                team_dto: TeamDTO = TeamService.get_team_by_id(team_id)
                return Response(data=team_dto.model_dump(mode="json"), status=status.HTTP_200_OK)
        except ValueError as e:
            fallback_response = ApiErrorResponse(
                statusCode=404,
                message=str(e),
                errors=[{"detail": str(e)}],
            )
            return Response(data=fallback_response.model_dump(mode="json"), status=404)
        except Exception as e:
            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}],
            )
            return Response(data=fallback_response.model_dump(mode="json"), status=500)
