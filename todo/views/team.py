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
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        - Example: `Cookie: todo-access=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...`
        
        **Role Hierarchy:** Owner > Admin > Member
        
        **Returned Information:**
        - Team details (id, name, description)
        - User's role in each team
        - Team member count and details
        
        **Test with curl:**
        ```bash
        curl -X GET "http://localhost:8000/v1/teams" \
             -H "Cookie: todo-access=<your-jwt-token>"
        ```
        """,
        tags=["teams"],
        responses={
            200: OpenApiResponse(
                response=GetUserTeamsResponse,
                description="User teams retrieved successfully",
                examples=[
                    OpenApiExample(
                        "User Teams Response",
                        summary="Teams with role information",
                        value={
                            "teams": [
                                {
                                    "id": "6879287077d79dd472916a3f",
                                    "name": "Complete RBAC Test Team",
                                    "description": "Testing comprehensive RBAC functionality",
                                    "user_role": "owner",
                                    "member_count": 1,
                                },
                                {
                                    "id": "6877fd91f100c14431250291",
                                    "name": "Development Team",
                                    "description": "Main development team",
                                    "user_role": "admin",
                                    "member_count": 3,
                                },
                            ]
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        },
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
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
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
        
        **Test with curl:**
        ```bash
        curl -X POST "http://localhost:8000/v1/teams" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{
               "name": "My Test Team",
               "description": "Testing team creation via Swagger"
             }'
        ```
        """,
        tags=["teams"],
        request=CreateTeamSerializer,
        responses={
            201: OpenApiResponse(
                response=CreateTeamResponse,
                description="Team created successfully, creator assigned as Owner",
                examples=[
                    OpenApiExample(
                        "Team Created Successfully",
                        summary="Successful team creation with owner role",
                        value={
                            "team": {
                                "id": "6879287077d79dd472916a3f",
                                "name": "My Test Team",
                                "description": "Testing team creation via Swagger",
                                "invite_code": "ABC123DEF",
                                "created_by": "686a451ad6706973cbd2ba30",
                                "user_role": "owner",
                            },
                            "message": "Team created successfully",
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Bad request - validation error"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            500: OpenApiResponse(description="Internal server error"),
        },
        examples=[
            OpenApiExample(
                "Create Team Request",
                summary="Basic team creation",
                value={
                    "name": "Development Team",
                    "description": "Main development team for project X",
                    "member_ids": [],
                    "poc_id": None,
                },
                request_only=True,
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
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Permission Requirements:**
        - Must be a team member to view team details
        - Returns 403 if user is not a team member
        
        **Optional Member Details:**
        - Set `?member=true` to get users belonging to this team
        - Includes role information for each member
        
        **Test with curl:**
        ```bash
        # Get team details
        curl -X GET "http://localhost:8000/v1/teams/6879287077d79dd472916a3f" \
             -H "Cookie: todo-access=<your-jwt-token>"
             
        # Get team members
        curl -X GET "http://localhost:8000/v1/teams/6879287077d79dd472916a3f?member=true" \
             -H "Cookie: todo-access=<your-jwt-token>"
        ```
        """,
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team (e.g., 6879287077d79dd472916a3f)",
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
            200: OpenApiResponse(
                description="Team or team members retrieved successfully",
                response=TeamDTO,
                examples=[
                    OpenApiExample(
                        "Team Details Response",
                        summary="Team information with role details",
                        value={
                            "id": "6879287077d79dd472916a3f",
                            "name": "Complete RBAC Test Team",
                            "description": "Testing comprehensive RBAC functionality",
                            "invite_code": "ABC123DEF",
                            "user_role": "owner",
                            "created_by": "686a451ad6706973cbd2ba30",
                            "member_count": 1,
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Permission denied - team membership required",
                examples=[
                    OpenApiExample(
                        "Team Membership Required",
                        value={
                            "error": "Team membership required",
                            "error_type": "membership_required",
                            "message": "Must be a member of team 6879287077d79dd472916a3f to view team",
                            "details": {"action": "view team", "team_id": "6879287077d79dd472916a3f"},
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
        summary="Update team details (Admin+ required)",
        description="""
        Update team information.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Permission Requirements:**
        - Requires **Admin** or **Owner** role in the team
        - Members cannot update team details
        
        **Updateable Fields:**
        - name: Team name
        - description: Team description
        - poc_id: Point of contact user ID
        - member_ids: Complete replacement of team members
        
        **Test with curl:**
        ```bash
        curl -X PATCH "http://localhost:8000/v1/teams/6879287077d79dd472916a3f" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{
               "name": "Updated Team Name",
               "description": "Updated team description"
             }'
        ```
        """,
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team (e.g., 6879287077d79dd472916a3f)",
            ),
        ],
        request=UpdateTeamSerializer,
        responses={
            200: OpenApiResponse(
                response=TeamDTO,
                description="Team updated successfully",
                examples=[
                    OpenApiExample(
                        "Team Updated Successfully",
                        summary="Updated team details",
                        value={
                            "id": "6879287077d79dd472916a3f",
                            "name": "Updated Team Name",
                            "description": "Updated team description",
                            "invite_code": "ABC123DEF",
                            "user_role": "owner",
                            "created_by": "686a451ad6706973cbd2ba30",
                            "member_count": 1,
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Bad request - validation error or invalid member IDs"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Permission denied - insufficient role",
                examples=[
                    OpenApiExample(
                        "Insufficient Role",
                        value={
                            "error": "Permission denied",
                            "error_type": "team_permission_denied",
                            "message": "Cannot update_team on team 6879287077d79dd472916a3f",
                            "details": {
                                "action": "update_team",
                                "team_id": "6879287077d79dd472916a3f",
                                "user_role": "member",
                            },
                        },
                    )
                ],
            ),
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
        operation_id="delete_team",
        summary="Delete team (Owner only)",
        description="""
        Delete a team permanently.
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Permission Requirements:**
        - Requires **Owner** role in the team
        - Admins and Members cannot delete teams
        
        **Warning:** This action implements soft deletion and will:
        - Mark team as deleted (is_deleted=true)
        - Remove all team memberships  
        - Unassign all team tasks
        - Team cannot be recovered through API
        
        **Test with curl:**
        ```bash
        curl -X DELETE "http://localhost:8000/v1/teams/6879287077d79dd472916a3f" \
             -H "Cookie: todo-access=<your-jwt-token>"
        ```
        
        **Expected Response:** HTTP 204 No Content
        """,
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team to delete (e.g., 6879287077d79dd472916a3f)",
            ),
        ],
        responses={
            204: OpenApiResponse(description="Team deleted successfully"),
            401: OpenApiResponse(
                description="Authentication required - missing or invalid JWT token",
                examples=[
                    OpenApiExample(
                        "Authentication Required",
                        value={
                            "detail": "Authentication credentials were not provided.",
                            "code": "authentication_required",
                        },
                    )
                ],
            ),
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
        try:
            user_id = request.user_id
            TeamService.delete_team(team_id, user_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            error_response = ApiErrorResponse(
                statusCode=404,
                message=str(e),
                errors=[{"detail": str(e)}],
            )
            return Response(data=error_response.model_dump(mode="json"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
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


class JoinTeamByInviteCodeView(APIView):
    @extend_schema(
        operation_id="join_team_by_invite_code",
        summary="Join a team by invite code",
        description="""
        Join a team using a valid invite code. 
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Default Role:** New members are assigned **Member** role by default
        
        **Test with curl:**
        ```bash
        curl -X POST "http://localhost:8000/v1/teams/join" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{"invite_code": "ABC123DEF"}'
        ```
        """,
        tags=["teams"],
        request=JoinTeamByInviteCodeSerializer,
        responses={
            200: OpenApiResponse(response=TeamDTO, description="Joined team successfully"),
            400: OpenApiResponse(description="Bad request - validation error or already a member"),
            401: OpenApiResponse(description="Authentication required"),
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
        summary="Add members to a team (Admin+ required)",
        description="""
        Add new members to a team. 
        
        **Authentication Required:**
        - Use cookie-based authentication: `Cookie: todo-access=<JWT_token>`
        
        **Permission Requirements:**
        - Requires **Admin** or **Owner** role in the team
        - Members cannot add other members
        
        **Default Role:** New members are assigned **Member** role by default
        
        **Test with curl:**
        ```bash
        curl -X POST "http://localhost:8000/v1/teams/6879287077d79dd472916a3f/members" \
             -H "Content-Type: application/json" \
             -H "Cookie: todo-access=<your-jwt-token>" \
             -d '{"member_ids": ["686a451ad6706973cbd2ba31", "686a451ad6706973cbd2ba32"]}'
        ```
        """,
        tags=["teams"],
        parameters=[
            OpenApiParameter(
                name="team_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the team (e.g., 6879287077d79dd472916a3f)",
            ),
        ],
        request=AddTeamMemberSerializer,
        responses={
            200: OpenApiResponse(response=TeamDTO, description="Team members added successfully"),
            400: OpenApiResponse(description="Bad request - validation error or user not a team member"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied - admin+ role required"),
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
