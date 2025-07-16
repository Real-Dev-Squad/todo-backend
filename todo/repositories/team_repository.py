import logging
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId

from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.repositories.common.mongo_repository import MongoRepository

logger = logging.getLogger(__name__)


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

        logger.info(f"Created team {team.id} with name '{team.name}'")
        return team

    @classmethod
    def get_by_id(cls, team_id: str) -> Optional[TeamModel]:
        """Get team by ID"""
        teams_collection = cls.get_collection()
        try:
            team_data = teams_collection.find_one({"_id": ObjectId(team_id), "is_deleted": False})
            if team_data:
                return TeamModel(**team_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving team {team_id}: {e}")
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

        logger.info(f"Added user {user_team.user_id} to team {user_team.team_id}")
        return user_team

    @classmethod
    def create_many(cls, user_teams: List[UserTeamDetailsModel]) -> List[UserTeamDetailsModel]:
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

        for i, user_team in enumerate(user_teams):
            user_team.id = insert_result.inserted_ids[i]

        logger.info(f"Batch created {len(user_teams)} user-team relationships")
        return user_teams

    @classmethod
    def get_by_user_id(cls, user_id: str) -> List[UserTeamDetailsModel]:
        """
        Get all team relationships for a specific user.
        """
        collection = cls.get_collection()
        try:
            user_teams_data = collection.find({"user_id": user_id, "is_active": True})
            return [UserTeamDetailsModel(**data) for data in user_teams_data]
        except Exception as e:
            logger.error(f"Error retrieving teams for user {user_id}: {e}")
            return []

    @classmethod
    def get_users_by_team_id(cls, team_id: str) -> List[str]:
        """
        Get all user IDs for a specific team.
        """
        collection = cls.get_collection()
        try:
            user_teams_data = list(collection.find({"team_id": team_id, "is_active": True}))
            return [data["user_id"] for data in user_teams_data]
        except Exception as e:
            logger.error(f"Error retrieving users for team {team_id}: {e}")
            return []

    @classmethod
    def get_user_infos_by_team_id(cls, team_id: str) -> List[dict]:
        """
        Get all user info (user_id, name, email) for a specific team.
        """
        from todo.repositories.user_repository import UserRepository

        user_ids = cls.get_users_by_team_id(team_id)
        user_infos = []

        for user_id in user_ids:
            try:
                user = UserRepository.get_by_id(user_id)
                if user:
                    user_infos.append({"user_id": user_id, "name": user.name, "email": user.email_id})
            except Exception as e:
                logger.warning(f"Error retrieving user info for {user_id}: {e}")
                continue

        return user_infos

    @classmethod
    def get_by_user_and_team(cls, user_id: str, team_id: str) -> Optional[UserTeamDetailsModel]:
        """Get user-team relationship"""
        collection = cls.get_collection()
        try:
            user_team_data = collection.find_one({"user_id": user_id, "team_id": team_id, "is_active": True})
            if user_team_data:
                return UserTeamDetailsModel(**user_team_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving user-team relationship for user {user_id} and team {team_id}: {e}")
            return None

    @classmethod
    def deactivate_user_team(cls, user_id: str, team_id: str) -> bool:
        """Deactivate user-team relationship"""
        collection = cls.get_collection()
        try:
            result = collection.update_one(
                {"user_id": user_id, "team_id": team_id},
                {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
            )
            success = result.modified_count > 0
            if success:
                logger.info(f"Deactivated user {user_id} from team {team_id}")
            return success
        except Exception as e:
            logger.error(f"Error deactivating user {user_id} from team {team_id}: {e}")
            return False
