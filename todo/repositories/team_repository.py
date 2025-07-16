from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.repositories.common.mongo_repository import MongoRepository


class TeamRepository(MongoRepository):
    collection_name = TeamModel.collection_name

    @classmethod
    def create(cls, team: TeamModel) -> TeamModel:
        """
        Creates a new team in the repository.
        """
        teams_collection = cls.get_collection()
        team.created_at = datetime.now(timezone.utc)
        team.updated_at = datetime.now(timezone.utc)

        team_dict = team.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = teams_collection.insert_one(team_dict)
        team.id = insert_result.inserted_id
        return team

    @classmethod
    def get_by_id(cls, team_id: str) -> Optional[TeamModel]:
        """
        Get a team by its ID.
        """
        teams_collection = cls.get_collection()
        try:
            team_data = teams_collection.find_one({"_id": ObjectId(team_id), "is_deleted": False})
            if team_data:
                return TeamModel(**team_data)
            return None
        except Exception:
            return None

    @classmethod
    def get_by_invite_code(cls, invite_code: str) -> Optional[TeamModel]:
        """
        Get a team by its invite code.
        """
        teams_collection = cls.get_collection()
        try:
            team_data = teams_collection.find_one({"invite_code": invite_code, "is_deleted": False})
            if team_data:
                return TeamModel(**team_data)
            return None
        except Exception:
            return None


class UserTeamDetailsRepository(MongoRepository):
    collection_name = UserTeamDetailsModel.collection_name

    @classmethod
    def create(cls, user_team: UserTeamDetailsModel) -> UserTeamDetailsModel:
        """
        Creates a new user-team relationship.
        """
        collection = cls.get_collection()
        user_team.created_at = datetime.now(timezone.utc)
        user_team.updated_at = datetime.now(timezone.utc)

        user_team_dict = user_team.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(user_team_dict)
        user_team.id = insert_result.inserted_id
        return user_team

    @classmethod
    def create_many(cls, user_teams: list[UserTeamDetailsModel]) -> list[UserTeamDetailsModel]:
        """
        Creates multiple user-team relationships.
        """
        collection = cls.get_collection()
        current_time = datetime.now(timezone.utc)

        for user_team in user_teams:
            user_team.created_at = current_time
            user_team.updated_at = current_time

        user_teams_dicts = [
            user_team.model_dump(mode="json", by_alias=True, exclude_none=True) for user_team in user_teams
        ]
        insert_result = collection.insert_many(user_teams_dicts)

        # Set the inserted IDs
        for i, user_team in enumerate(user_teams):
            user_team.id = insert_result.inserted_ids[i]

        return user_teams

    @classmethod
    def get_by_user_id(cls, user_id: str) -> list[UserTeamDetailsModel]:
        """
        Get all team relationships for a specific user.
        """
        collection = cls.get_collection()
        try:
            user_teams_data = collection.find({"user_id": user_id, "is_active": True})
            return [UserTeamDetailsModel(**data) for data in user_teams_data]
        except Exception:
            return []

    @classmethod
    def get_users_by_team_id(cls, team_id: str) -> list[str]:
        """
        Get all user IDs for a specific team.
        """
        collection = cls.get_collection()
        try:
            user_teams_data = list(collection.find({"team_id": team_id, "is_active": True}))
            return [data["user_id"] for data in user_teams_data]
        except Exception:
            return []

    @classmethod
    def get_user_infos_by_team_id(cls, team_id: str) -> list[dict]:
        """
        Get all user info (user_id, name, email) for a specific team.
        """
        from todo.repositories.user_repository import UserRepository

        user_ids = cls.get_users_by_team_id(team_id)
        user_infos = []
        for user_id in user_ids:
            user = UserRepository.get_by_id(user_id)
            if user:
                user_infos.append({"user_id": user_id, "name": user.name, "email": user.email_id})
        return user_infos
