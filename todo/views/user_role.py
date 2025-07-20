from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from todo.services.user_role_service import UserRoleService

logger = logging.getLogger(__name__)


class UserRoleListView(APIView):
    def get(self, request, user_id: str):
        scope = request.query_params.get("scope")
        user_roles = UserRoleService.get_user_roles(user_id, scope)

        return Response({"user_id": user_id, "roles": user_roles, "total": len(user_roles)})


class TeamUserRoleListView(APIView):
    def get(self, request, team_id: str):
        from todo.repositories.user_role_repository import UserRoleRepository
        from todo.repositories.user_repository import UserRepository

        team_users = []

        # Get all team user roles
        collection = UserRoleRepository.get_collection()
        user_roles_docs = collection.find({"team_id": team_id, "scope": "TEAM", "is_active": True})

        for doc in user_roles_docs:
            user = UserRepository.get_by_id(doc["user_id"])
            if user:
                team_users.append({"user_id": doc["user_id"], "user_name": user.name, "role_name": doc["role_name"]})

        return Response({"team_id": team_id, "users": team_users, "total": len(team_users)})


class TeamUserRoleDetailView(APIView):
    def get(self, request, team_id: str, user_id: str):
        user_roles = UserRoleService.get_user_roles(user_id, "TEAM", team_id)

        return Response({"team_id": team_id, "user_id": user_id, "roles": user_roles})

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

    def delete(self, request, team_id: str, user_id: str):
        role_name = request.data.get("role_name")
        if not role_name:
            return Response({"error": "role_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        success = UserRoleService.remove_role(user_id, role_name, "TEAM", team_id)

        if success:
            return Response(
                {
                    "message": f"Role '{role_name}' removed from user {user_id}",
                    "team_id": team_id,
                    "user_id": user_id,
                    "role_name": role_name,
                }
            )
        else:
            return Response({"message": f"Role '{role_name}' not found for user {user_id}"})
