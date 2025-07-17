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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from todo.dto.team_dto import TeamDTO
from todo.services.user_service import UserService


class TeamListView(APIView):
    @extend_schema(
        operation_id="get_user_teams",
        summary="Get user's teams with role information",
        description="""
        Get all teams assigned to the authenticated user with their role information.
        
        **Role Hierarchy:** Owner > Admin > Member
        
        **Returned Information:**
        - Team details
        - User's role in each team
        - Team member count and details
        """,
        tags=["teams"],
        responses={
            200: OpenApiResponse(response=GetUserTeamsResponse, description="User teams retrieved successfully"),
            401: OpenApiResponse(description="Authentication required"),
            500: OpenApiResponse(description="Internal server error"),
        },
        examples=[
            OpenApiExample(
                "User Teams Response",
                summary="Example teams with role information",
                value={
                    "teams": [
                        {
                            "id": "team_id_1",
                            "name": "Development Team",
                            "description": "Main dev team",
                            "user_role": "owner",
                            "member_count": 5,
                        },
                        {
                            "id": "team_id_2",
                            "name": "Marketing Team",
                            "description": "Marketing activities",
                            "user_role": "admin",
                            "member_count": 3,
                        },
                    ]
                },
                response_only=True,
            ),
        ],
    )
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

    @extend_schema(
        operation_id="create_team",
        summary="Create a new team",
        description="""
        Create a new team with the provided details. 
        
        **Automatic Role Assignment:**
        - Creator is automatically assigned as the team **Owner**
        - Owners have full permissions including team deletion and admin management
        
        **Role Permissions:**
        - **Owner**: All operations (delete team, manage admins/members)  
        - **Admin**: Update team, add/remove members (not other admins/owners)
        - **Member**: View team, create tasks
        
        **Team Features:**
        - Auto-generated invite code for easy team joining
        - Hierarchical permission system
        """,
        tags=["teams"],
        request=CreateTeamSerializer,
        responses={
            201: OpenApiResponse(
                response=CreateTeamResponse, description="Team created successfully, creator assigned as Owner"
            ),
            400: OpenApiResponse(description="Bad request - validation error"),
            401: OpenApiResponse(description="Authentication required"),
            500: OpenApiResponse(description="Internal server error"),
        },
        examples=[
            OpenApiExample(
                "Create Team Request",
                summary="Example team creation",
                value={
                    "name": "Development Team",
                    "description": "Main development team for project X",
                    "member_ids": [],
                    "poc_id": None,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Team Response",
                summary="Successful team creation with owner role",
                value={
                    "team": {
                        "id": "team_id_123",
                        "name": "Development Team",
                        "description": "Main development team for project X",
                        "invite_code": "ABC123",
                        "created_by": "user_id_456",
                        "user_role": "owner",
                    },
                    "message": "Team created successfully",
                },
                response_only=True,
            ),
        ],
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
        description="""
        Retrieve a single team by its unique identifier.
        
        **Permission Requirements:**
        - Must be a team member to view team details
        - Returns 403 if user is not a team member
        
        **Optional Member Details:**
        - Set `?member=true` to get users belonging to this team
        - Includes role information for each member
        """,
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
            200: OpenApiResponse(description="Team or team members retrieved successfully", response=TeamDTO),
            403: OpenApiResponse(
                description="Permission denied - team membership required",
                examples=[
                    OpenApiExample(
                        "Team Membership Required",
                        value={
                            "error": "Team membership required",
                            "error_type": "membership_required",
                            "message": "Must be a member of team team_id to view team",
                            "details": {"action": "view team", "team_id": "team_id"},
                        },
                    )
                ],
            ),
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

            return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)

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

    @extend_schema(
        operation_id="update_team",
        summary="Update team details (Admin+ required)",
        description="""
        Update team information.
        
        **Permission Requirements:**
        - Requires **Admin** or **Owner** role in the team
        - Members cannot update team details
        """,
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Team updated successfully"),
            403: OpenApiResponse(
                description="Permission denied - insufficient role",
                examples=[
                    OpenApiExample(
                        "Insufficient Role",
                        value={
                            "error": "Permission denied",
                            "error_type": "team_permission_denied",
                            "message": "Cannot update_team on team team_id",
                            "details": {"action": "update_team", "team_id": "team_id", "user_role": "member"},
                        },
                    )
                ],
            ),
            404: OpenApiResponse(description="Team not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    @extend_schema(
        operation_id="delete_team",
        summary="Delete team (Owner only)",
        description="""
        Delete a team permanently.
        
        **Permission Requirements:**
        - Requires **Owner** role in the team
        - Admins and Members cannot delete teams
        
        **Warning:** This action is irreversible and will:
        - Remove all team memberships
        - Unassign all team tasks
        - Delete the team permanently
        """,
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Team deleted successfully"),
            403: OpenApiResponse(
                description="Permission denied - owner role required",
                examples=[
                    OpenApiExample(
                        "Owner Role Required",
                        value={
                            "error": "Insufficient role",
                            "error_type": "insufficient_role",
                            "message": "Action 'delete team' requires 'owner' role",
                            "details": {"action": "delete team", "current_role": "admin", "required_role": "owner"},
                        },
                    )
                ],
            ),
            404: OpenApiResponse(description="Team not found"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def delete(self, request: Request, team_id: str):
        """Delete team (requires Owner role)"""
        pass


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
            return Response(data=team_dto.model_dump(mode="json"), status=status.HTTP_200_OK)
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

            return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)

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
