from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from todo.services.user_role_service import UserRoleService


class UserRoleListView(APIView):
    def get(self, request, user_id: str):
        scope = request.query_params.get("scope")
        user_roles = UserRoleService.get_user_roles(user_id, scope)

        return Response({"user_id": user_id, "roles": user_roles, "total": len(user_roles)})


class TeamUserRoleListView(APIView):
    def get(self, request, team_id: str):
        team_users = UserRoleService.get_team_users_with_roles(team_id)
        return Response({"team_id": team_id, "users": team_users, "total": len(team_users)})


class TeamUserRoleDetailView(APIView):
    def get(self, request, team_id: str, user_id: str):
        user_roles = UserRoleService.get_user_roles(user_id, "TEAM", team_id)
        return Response({"team_id": team_id, "user_id": user_id, "roles": user_roles})

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {"role_name": {"type": "string"}},
                "required": ["role_name"],
                "example": {"role_name": "admin"},
            }
        },
        examples=[
            OpenApiExample("Assign Role Example", value={"role_name": "admin"}, request_only=True, response_only=False)
        ],
    )
    def post(self, request, team_id: str, user_id: str):
        role_name = request.data.get("role_name")
        if not role_name:
            return Response({"error": "role_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        success = UserRoleService.assign_role(user_id, role_name, "TEAM", team_id)

        if success:
            return Response(
                {
                    "message": f"Role '{role_name}' assigned to user {user_id}",
                    "team_id": team_id,
                    "user_id": user_id,
                    "role_name": role_name,
                }
            )
        else:
            return Response({"error": "Failed to assign role"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TeamUserRoleDeleteView(APIView):
    @extend_schema(
        parameters=[
            {
                "name": "role_id",
                "in": "path",
                "required": True,
                "description": "The ID of the role to remove",
                "schema": {"type": "string"},
            }
        ],
        examples=[
            OpenApiExample(
                "Remove Role Example",
                value={"role_id": "60d5f9f8f8f8f8f8f8f8f8f8"},
                request_only=True,
                response_only=False,
            )
        ],
    )
    def delete(self, request, team_id: str, user_id: str, role_id: str):
        success = UserRoleService.remove_role_by_id(user_id, role_id, "TEAM", team_id)

        if success:
            return Response(
                {
                    "message": f"Role with ID '{role_id}' removed from user {user_id}",
                    "team_id": team_id,
                    "user_id": user_id,
                    "role_id": role_id,
                }
            )
        else:
            return Response({"message": f"Role with ID '{role_id}' not found for user {user_id}"})
