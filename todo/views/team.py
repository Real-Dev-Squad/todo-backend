from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request
from django.conf import settings

from todo.serializers.create_team_serializer import CreateTeamSerializer, JoinTeamByInviteCodeSerializer
from todo.serializers.update_team_serializer import UpdateTeamSerializer
from todo.serializers.add_team_member_serializer import AddTeamMemberSerializer
from todo.services.team_service import TeamService
from todo.dto.team_dto import CreateTeamDTO
from todo.dto.update_team_dto import UpdateTeamDTO
from todo.dto.responses.create_team_response import CreateTeamResponse
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from todo.constants.messages import ApiErrors
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.dto.team_dto import TeamDTO
from todo.services.user_service import UserService
from todo.repositories.team_repository import TeamRepository
from todo.repositories.audit_log_repository import AuditLogRepository
from todo.models.audit_log import AuditLogModel
from todo.repositories.user_repository import UserRepository
from todo.repositories.task_repository import TaskRepository


class TeamListView(APIView):
    def get(self, request: Request):
        """
        Get all teams assigned to the authenticated user.
        """
        try:
            user_id = request.user_id
            response: GetUserTeamsResponse = TeamService.get_user_teams(user_id)
            data = response.model_dump(mode="json")
            for team in data.get("teams", []):
                team.pop("invite_code", None)
            return Response(data=data, status=status.HTTP_200_OK)

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

    @extend_schema(
        operation_id="create_team",
        summary="Create a new team",
        description="Create a new team with the provided details. The creator is always added as a member, even if not in member_ids or as POC.",
        tags=["teams"],
        request=CreateTeamSerializer,
        responses={
            201: OpenApiResponse(response=CreateTeamResponse, description="Team created successfully"),
            400: OpenApiResponse(description="Bad request - validation error"),
            500: OpenApiResponse(description="Internal server error"),
        },
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
            data = response.model_dump(mode="json")
            # Remove invite_code from the created team
            if "team" in data:
                data["team"].pop("invite_code", None)
            return Response(data=data, status=status.HTTP_201_CREATED)

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
            team_dto: TeamDTO = TeamService.get_team_by_id(team_id)
            member = request.query_params.get("member", "false").lower() == "true"
            if member:
                users = UserService.get_users_by_team_id(team_id)
                users_data = [user.dict() for user in users]
                team_dto.users = users_data
            data = team_dto.model_dump(mode="json")
            data.pop("invite_code", None)
            return Response(data=data, status=status.HTTP_200_OK)
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

    @extend_schema(
        operation_id="update_team",
        summary="Update team by ID",
        description="Update a team's details including name, description, point of contact (POC), and team members. All fields are optional - only include the fields you want to update. For member management: if member_ids is provided, it completely replaces the current team members; if member_ids is not provided, existing members remain unchanged.",
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
            ),
        ],
        request=UpdateTeamSerializer,
        responses={
            200: OpenApiResponse(response=TeamDTO, description="Team updated successfully"),
            400: OpenApiResponse(description="Bad request - validation error or invalid member IDs"),
            404: OpenApiResponse(description="Team not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def patch(self, request: Request, team_id: str):
        """
        Update a team by ID.
        """
        serializer = UpdateTeamSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        try:
            dto = UpdateTeamDTO(**serializer.validated_data)
            updated_by_user_id = request.user_id
            response: TeamDTO = TeamService.update_team(team_id, dto, updated_by_user_id)
            data = response.model_dump(mode="json")
            data.pop("invite_code", None)
            return Response(data=data, status=status.HTTP_200_OK)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                error_response = e.args[0]
                return Response(data=error_response.model_dump(mode="json"), status=error_response.statusCode)

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


class JoinTeamByInviteCodeView(APIView):
    @extend_schema(
        operation_id="join_team_by_invite_code",
        summary="Join a team by invite code",
        description="Join a team using a valid invite code. Returns the joined team details.",
        tags=["teams"],
        request=JoinTeamByInviteCodeSerializer,
        responses={
            200: OpenApiResponse(response=TeamDTO, description="Joined team successfully"),
            400: OpenApiResponse(description="Bad request - validation error or already a member"),
            404: OpenApiResponse(description="Team not found or invalid invite code"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        serializer = JoinTeamByInviteCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = request.user_id
            invite_code = serializer.validated_data["invite_code"]
            team_dto = TeamService.join_team_by_invite_code(invite_code, user_id)
            data = team_dto.model_dump(mode="json")
            data.pop("invite_code", None)
            return Response(data=data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddTeamMembersView(APIView):
    @extend_schema(
        operation_id="add_team_members",
        summary="Add members to a team",
        description="Add new members to a team. Only existing team members can add other members.",
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
            ),
        ],
        request=AddTeamMemberSerializer,
        responses={
            200: OpenApiResponse(response=TeamDTO, description="Team members added successfully"),
            400: OpenApiResponse(description="Bad request - validation error or user not a team member"),
            404: OpenApiResponse(description="Team not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request, team_id: str):
        """
        Add members to a team. Only existing team members can add other members.
        """
        serializer = AddTeamMemberSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        try:
            member_ids = serializer.validated_data["member_ids"]
            added_by_user_id = request.user_id
            response: TeamDTO = TeamService.add_team_members(team_id, member_ids, added_by_user_id)
            data = response.model_dump(mode="json")
            data.pop("invite_code", None)
            return Response(data=data, status=status.HTTP_200_OK)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                error_response = e.args[0]
                return Response(data=error_response.model_dump(mode="json"), status=error_response.statusCode)

            fallback_response = ApiErrorResponse(
                statusCode=400,
                message=str(e),
                errors=[{"detail": str(e)}],
            )
            return Response(data=fallback_response.model_dump(mode="json"), status=400)
        except Exception as e:
            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}],
            )
            return Response(data=fallback_response.model_dump(mode="json"), status=500)

    def _handle_validation_errors(self, errors):
        """Handle validation errors and return appropriate response."""
        error_response = ApiErrorResponse(
            statusCode=400,
            message=ApiErrors.VALIDATION_ERROR,
            errors=[{"detail": str(error)} for error in errors.values()],
        )
        return Response(data=error_response.model_dump(mode="json"), status=400)


class TeamInviteCodeView(APIView):
    @extend_schema(
        operation_id="get_team_invite_code",
        summary="Get team invite code (creator or POC only)",
        description="Return the invite code for a team if the requesting user is the creator or POC of the team.",
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Invite code returned successfully"),
            403: OpenApiResponse(description="Forbidden - not creator or POC"),
            404: OpenApiResponse(description="Team not found"),
        },
    )
    def get(self, request: Request, team_id: str):
        """
        Return the invite code for a team if the requesting user is the creator or POC of the team.
        """
        user_id = request.user_id
        team = TeamRepository.get_by_id(team_id)
        if not team:
            return Response({"detail": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
        is_creator = str(team.created_by) == str(user_id)
        is_poc = str(team.poc_id) == str(user_id)
        if is_creator or is_poc:
            return Response({"invite_code": team.invite_code}, status=status.HTTP_200_OK)
        return Response(
            {"detail": "You are not authorized to view the invite code for this team."},
            status=status.HTTP_403_FORBIDDEN,
        )


class TeamActivityTimelineView(APIView):
    @extend_schema(
        operation_id="get_team_activity_timeline",
        summary="Get team activity timeline",
        description="Return a timeline of all activities related to tasks assigned to the team, including assignment, unassignment, executor changes, and status changes. All IDs are replaced with names.",
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "timeline": {
                            "type": "array",
                            "items": {"type": "object"},
                        }
                    },
                },
                description="Team activity timeline returned successfully"
            ),
            404: OpenApiResponse(description="Team not found"),
        },
    )
    def get(self, request: Request, team_id: str):
        team = TeamRepository.get_by_id(team_id)
        if not team:
            return Response({"detail": "Team not found."}, status=status.HTTP_404_NOT_FOUND)
        logs = AuditLogRepository.get_by_team_id(team_id)
        # Pre-fetch team name
        team_name = team.name
        # Pre-fetch all user and task names needed
        user_ids = set()
        task_ids = set()
        for log in logs:
            if log.performed_by:
                user_ids.add(str(log.performed_by))
            if log.spoc_id:
                user_ids.add(str(log.spoc_id))
            if log.previous_executor_id:
                user_ids.add(str(log.previous_executor_id))
            if log.new_executor_id:
                user_ids.add(str(log.new_executor_id))
            if log.task_id:
                task_ids.add(str(log.task_id))
        user_map = {str(u.id): u.name for u in UserRepository.get_by_ids(list(user_ids))}
        task_map = {str(t.id): t.title for t in TaskRepository.get_by_ids(list(task_ids))}
        timeline = []
        for log in logs:
            entry = {
                "action": log.action,
                "timestamp": log.timestamp,
            }
            if log.task_id:
                entry["task_title"] = task_map.get(str(log.task_id), str(log.task_id))
            if log.team_id:
                entry["team_name"] = team_name
            if log.performed_by:
                entry["performed_by_name"] = user_map.get(str(log.performed_by), str(log.performed_by))
            if log.spoc_id:
                entry["spoc_name"] = user_map.get(str(log.spoc_id), str(log.spoc_id))
            if log.previous_executor_id:
                entry["previous_executor_name"] = user_map.get(str(log.previous_executor_id), str(log.previous_executor_id))
            if log.new_executor_id:
                entry["new_executor_name"] = user_map.get(str(log.new_executor_id), str(log.new_executor_id))
            if log.status_from:
                entry["status_from"] = log.status_from
            if log.status_to:
                entry["status_to"] = log.status_to
            timeline.append(entry)
        return Response({"timeline": timeline}, status=status.HTTP_200_OK)
