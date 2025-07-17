import logging
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from pymongo import ReturnDocument

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

    @classmethod
    def update(cls, team_id: str, update_data: dict, updated_by_user_id: str) -> Optional[TeamModel]:
        """
        Update a team by its ID using atomic operation to prevent race conditions.
        """
        teams_collection = cls.get_collection()
        try:
            # Add updated_by and updated_at fields
            update_data["updated_by"] = updated_by_user_id
            update_data["updated_at"] = datetime.now(timezone.utc)

            # Remove None values to avoid overwriting with None
            update_data = {k: v for k, v in update_data.items() if v is not None}

            # Use find_one_and_update for atomicity - prevents race conditions
            updated_doc = teams_collection.find_one_and_update(
                {"_id": ObjectId(team_id), "is_deleted": False},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )

            if updated_doc:
                return TeamModel(**updated_doc)
            return None
        except Exception:
            return None

    @classmethod
    def delete_by_id(cls, team_id: str, user_id: str) -> TeamModel | None:
        """Soft delete team by setting is_deleted=True"""
        teams_collection = cls.get_collection()
        try:
            team_data = teams_collection.find_one({"_id": ObjectId(team_id), "is_deleted": False})
            if not team_data:
                return None

            deleted_team_data = teams_collection.find_one_and_update(
                {"_id": ObjectId(team_id)},
                {
                    "$set": {
                        "is_deleted": True,
                        "updated_at": datetime.now(timezone.utc),
                        "updated_by": ObjectId(user_id),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )

            if deleted_team_data:
                return TeamModel(**deleted_team_data)
            return None
        except Exception as e:
            logger.error(f"Error deleting team {team_id}: {e}")
            return None

    def is_user_spoc(cls, team_id: str, user_id: str) -> bool:
        """
        Check if the given user is the SPOC (poc_id) for the given team.
        """
        team = cls.get_by_id(team_id)
        if not team or not team.poc_id:
            return False
        return str(team.poc_id) == str(user_id)


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
    def get_users_and_added_on_by_team_id(cls, team_id: str) -> list[dict]:
        """
        Get all user IDs and their addedOn (created_at) for a specific team.
        """
        collection = cls.get_collection()
        try:
            user_teams_data = list(collection.find({"team_id": team_id, "is_active": True}))
            return [{"user_id": data["user_id"], "added_on": data.get("created_at")} for data in user_teams_data]
        except Exception:
            return []

    @classmethod
    def get_by_team_id(cls, team_id: str) -> list[UserTeamDetailsModel]:
        """
        Get all user-team relationships for a specific team.
        """
        collection = cls.get_collection()
        try:
            user_teams_data = collection.find({"team_id": team_id, "is_active": True})
            return [UserTeamDetailsModel(**data) for data in user_teams_data]
        except Exception:
            return []

    @classmethod
    def remove_user_from_team(cls, team_id: str, user_id: str, updated_by_user_id: str) -> bool:
        """
        Remove a user from a team by setting is_active to False.
        """
        collection = cls.get_collection()
        try:
            result = collection.update_one(
                {"team_id": team_id, "user_id": user_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": updated_by_user_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def add_user_to_team(
        cls, team_id: str, user_id: str, role_id: str, created_by_user_id: str
    ) -> UserTeamDetailsModel:
        """
        Add a user to a team.
        """
        collection = cls.get_collection()
        # Check if user is already in the team
        existing_relationship = collection.find_one({"team_id": team_id, "user_id": user_id})

        if existing_relationship:
            # If user exists but is inactive, reactivate them
            if not existing_relationship.get("is_active", True):
                collection.update_one(
                    {"_id": existing_relationship["_id"]},
                    {
                        "$set": {
                            "is_active": True,
                            "role_id": role_id,
                            "updated_by": created_by_user_id,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
                return UserTeamDetailsModel(**existing_relationship)
            else:
                # User is already active in the team
                return UserTeamDetailsModel(**existing_relationship)

        # Create new relationship
        user_team = UserTeamDetailsModel(
            user_id=user_id,
            team_id=team_id,
            role_id=role_id,
            is_active=True,
            created_by=created_by_user_id,
            updated_by=created_by_user_id,
        )
        return cls.create(user_team)

    @classmethod
    def update_team_members(cls, team_id: str, member_ids: list[str], updated_by_user_id: str) -> bool:
        """
        Update team members by replacing the current members with the new list.
        """
        try:
            # Get current team members
            current_members = cls.get_users_by_team_id(team_id)

            # Find members to remove (in current but not in new list)
            members_to_remove = [user_id for user_id in current_members if user_id not in member_ids]

            # Find members to add (in new list but not in current)
            members_to_add = [user_id for user_id in member_ids if user_id not in current_members]

            # Remove members
            for user_id in members_to_remove:
                cls.remove_user_from_team(team_id, user_id, updated_by_user_id)

            # Add new members
            for user_id in members_to_add:
                cls.add_user_to_team(team_id, user_id, "1", updated_by_user_id)  # Default role_id is "1"

            return True
        except Exception:
            return False

    @classmethod
    def update_user_role_in_team(cls, team_id: str, user_id: str, new_role_id: str, updated_by_user_id: str) -> bool:
        """
        Update a user's role in a team.
        """
        collection = cls.get_collection()
        try:
            result = collection.update_one(
                {"team_id": team_id, "user_id": user_id, "is_active": True},
                {
                    "$set": {
                        "role_id": new_role_id,
                        "updated_by": updated_by_user_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.modified_count > 0
        except Exception:
            return False
