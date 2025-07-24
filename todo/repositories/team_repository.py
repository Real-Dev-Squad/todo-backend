from datetime import datetime, timezone
from typing import Optional
from pymongo import ReturnDocument
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from todo.utils.retry_utils import retry
from django.db import transaction
from todo.models.postgres.team import Team as PostgresTeam
from todo.models.postgres.user_team_details import UserTeamDetails as PostgresUserTeamDetails
import uuid

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
            team_data = teams_collection.find_one({"_id": team_id, "is_deleted": False})
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
                {"_id": team_id, "is_deleted": False},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )

            if updated_doc:
                return TeamModel(**updated_doc)
            return None
        except Exception:
            return None

    @classmethod
    def is_user_spoc(cls, team_id: str, user_id: str) -> bool:
        """
        Check if the given user is the SPOC (poc_id) for the given team.
        """
        team = cls.get_by_id(team_id)
        if not team or not team.poc_id:
            return False
        return str(team.poc_id) == str(user_id)

    @classmethod
    def is_user_team_member(cls, team_id: str, user_id: str) -> bool:
        """
        Check if the given user is a member of the given team.
        """
        team_members = UserTeamDetailsRepository.get_users_by_team_id(team_id)
        return user_id in team_members

    @classmethod
    def create_parallel(cls, team: TeamModel) -> TeamModel:
        teams_collection = cls.get_collection()
        new_team_id = str(uuid.uuid4())
        team.created_at = datetime.now(timezone.utc)
        team.updated_at = datetime.now(timezone.utc)
        team_dict = team.model_dump(mode="json", by_alias=True, exclude_none=True)
        team_dict["_id"] = new_team_id

        def write_mongo():
            insert_result = teams_collection.insert_one(team_dict)
            return insert_result.inserted_id

        def write_postgres():
            with transaction.atomic():
                PostgresTeam.objects.create(
                    id=new_team_id,
                    name=team.name,
                    description=team.description,
                    poc_id=team.poc_id,
                    invite_code=team.invite_code,
                    created_by_id=team.created_by,
                    created_at=team.created_at,
                    is_deleted=team.is_deleted,
                )
                return "postgres_success"

        exceptions = []
        mongo_id = None
        postgres_done = False

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if isinstance(res, str) and res == "postgres_success":
                        postgres_done = True
                    else:
                        mongo_id = res
                except Exception as exc:
                    exceptions.append(exc)
                    print(f"[ERROR] Write failed: {exc}")

        # Compensation logic
        if exceptions:
            if mongo_id and not postgres_done:
                teams_collection.delete_one({"_id": new_team_id})
                print(f"[COMPENSATION] Rolled back Mongo for team {new_team_id}")
            if postgres_done and not mongo_id:
                with transaction.atomic():
                    PostgresTeam.objects.filter(id=new_team_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for team {new_team_id}")
            raise Exception(f"Team creation failed: {exceptions}")

        team.id = mongo_id
        return team

    @classmethod
    def update_parallel(cls, team_id: str, update_data: dict, updated_by_user_id: str) -> Optional[TeamModel]:
        teams_collection = cls.get_collection()
        now = datetime.now(timezone.utc)
        exceptions = []
        mongo_result = None
        postgres_done = False

        original_mongo = teams_collection.find_one({"_id": team_id, "is_deleted": False})
        try:
            original_postgres = PostgresTeam.objects.get(id=team_id, is_deleted=False)
        except PostgresTeam.DoesNotExist:
            original_postgres = None

        def update_mongo():
            update_data_mongo = {**update_data, "updated_by": updated_by_user_id, "updated_at": now}
            update_data_mongo = {k: v for k, v in update_data_mongo.items() if v is not None}
            updated_doc = teams_collection.find_one_and_update(
                {"_id": team_id, "is_deleted": False},
                {"$set": update_data_mongo},
                return_document=ReturnDocument.AFTER,
            )
            if not updated_doc:
                raise Exception("MongoDB update failed: No document updated.")
            return updated_doc

        def update_postgres():
            with transaction.atomic():
                try:
                    pg_team = PostgresTeam.objects.get(id=team_id, is_deleted=False)
                except PostgresTeam.DoesNotExist:
                    raise Exception("Postgres update failed: Team does not exist.")
                for k, v in update_data.items():
                    if hasattr(pg_team, k) and v is not None:
                        setattr(pg_team, k, v)
                pg_team.updated_by = updated_by_user_id
                pg_team.updated_at = now
                pg_team.save()
                return "postgres_success"

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(update_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(update_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if res == "postgres_success":
                        postgres_done = True
                    else:
                        mongo_result = res
                except Exception as exc:
                    exceptions.append(exc)
                    print(f"[ERROR] Update failed: {exc}")

        # Compensation logic
        if exceptions:
            if mongo_result and not postgres_done and original_mongo:
                teams_collection.replace_one({"_id": team_id}, original_mongo)
                print(f"[COMPENSATION] Rolled back Mongo update for team {team_id}")
            if postgres_done and not mongo_result and original_postgres:
                with transaction.atomic():
                    pg_team = PostgresTeam.objects.get(id=team_id, is_deleted=False)
                    for k, v in original_postgres.__dict__.items():
                        if not k.startswith("_") and hasattr(pg_team, k):
                            setattr(pg_team, k, v)
                    pg_team.save()
                    print(f"[COMPENSATION] Rolled back Postgres update for team {team_id}")
            raise Exception(f"Team update failed: {exceptions}")

        return TeamModel(**mongo_result) if mongo_result else None


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
    def add_user_from_team(
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
    def create_parallel(cls, user_team: UserTeamDetailsModel) -> UserTeamDetailsModel:
        collection = cls.get_collection()
        new_user_team_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_team.created_at = now
        user_team.updated_at = None
        user_team_dict = user_team.model_dump(mode="json", by_alias=True, exclude_none=True)
        user_team_dict["_id"] = new_user_team_id

        def write_mongo():
            insert_result = collection.insert_one(user_team_dict)
            return insert_result.inserted_id

        def write_postgres():
            with transaction.atomic():
                PostgresUserTeamDetails.objects.create(
                    id=new_user_team_id,
                    user_id=user_team.user_id,
                    team_id=user_team.team_id,
                    is_active=user_team.is_active,
                    role=user_team.role_id,
                    created_at=now,
                    updated_at=None,
                    created_by_id=user_team.created_by,
                    updated_by=None,
                )
                return "postgres_success"

        exceptions = []
        mongo_id = None
        postgres_done = False

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if isinstance(res, str) and res == "postgres_success":
                        postgres_done = True
                    else:
                        mongo_id = res
                except Exception as exc:
                    exceptions.append(exc)
                    print(f"[ERROR] Write failed: {exc}")

        # Compensation logic
        if exceptions:
            if mongo_id and not postgres_done:
                collection.delete_one({"_id": new_user_team_id})
                print(f"[COMPENSATION] Rolled back Mongo for user_team_details {new_user_team_id}")
            if postgres_done and not mongo_id:
                with transaction.atomic():
                    PostgresUserTeamDetails.objects.filter(id=new_user_team_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for user_team_details {new_user_team_id}")
            raise Exception(f"UserTeamDetails creation failed: {exceptions}")

        user_team.id = mongo_id
        return user_team

    @classmethod
    def create_many_parallel(cls, user_teams: list[UserTeamDetailsModel]) -> list[UserTeamDetailsModel]:
        results = []
        for user_team in user_teams:
            results.append(cls.create_parallel(user_team))
        return results

    @classmethod
    def update_team_members_parallel(cls, team_id: str, member_ids: list[str], updated_by_user_id: str) -> bool:
        """
        Update team members by replacing the current members with the new list in both MongoDB and Postgres in parallel.
        Compensation logic is applied if one update fails.
        Args:
            team_id (str): The team ID
            member_ids (list[str]): The new list of user IDs
            updated_by_user_id (str): The user performing the update
        Returns:
            bool: True if both DBs updated, else raises Exception
        """
        collection = cls.get_collection()
        now = datetime.now(timezone.utc)
        exceptions = []
        mongo_done = False
        postgres_done = False
        # Save originals for compensation
        original_mongo = list(collection.find({"team_id": team_id, "is_active": True}))
        from todo.models.postgres.user_team_details import UserTeamDetails as PostgresUserTeamDetails

        original_postgres = list(PostgresUserTeamDetails.objects.filter(team_id=team_id, is_active=True))

        def update_mongo():
            # Remove all current members
            collection.update_many(
                {"team_id": team_id, "is_active": True},
                {"$set": {"is_active": False, "updated_by": updated_by_user_id, "updated_at": now}},
            )
            # Add new members
            for user_id in member_ids:
                existing = collection.find_one({"team_id": team_id, "user_id": user_id})
                if existing:
                    if not existing.get("is_active", True):
                        collection.update_one(
                            {"_id": existing["_id"]},
                            {"$set": {"is_active": True, "updated_by": updated_by_user_id, "updated_at": now}},
                        )
                else:
                    user_team = {
                        "user_id": user_id,
                        "team_id": team_id,
                        "is_active": True,
                        "created_by": updated_by_user_id,
                        "updated_by": updated_by_user_id,
                        "created_at": now,
                        "updated_at": now,
                        "role_id": "1",  # Default role
                    }
                    collection.insert_one(user_team)
            return True

        def update_postgres():
            with transaction.atomic():
                # Remove all current members
                PostgresUserTeamDetails.objects.filter(team_id=team_id, is_active=True).update(
                    is_active=False, updated_by_id=updated_by_user_id, updated_at=now
                )
                # Add new members
                for user_id in member_ids:
                    existing = PostgresUserTeamDetails.objects.filter(team_id=team_id, user_id=user_id).first()
                    if existing:
                        if not existing.is_active:
                            existing.is_active = True
                            existing.updated_by_id = updated_by_user_id
                            existing.updated_at = now
                            existing.save()
                    else:
                        PostgresUserTeamDetails.objects.create(
                            user_id=user_id,
                            team_id=team_id,
                            is_active=True,
                            role_id="1",  # Default role
                            created_by_id=updated_by_user_id,
                            updated_by_id=updated_by_user_id,
                            created_at=now,
                            updated_at=now,
                        )
            return True

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(update_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(update_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if res is True:
                        if future == future_mongo:
                            mongo_done = True
                        else:
                            postgres_done = True
                except Exception as exc:
                    exceptions.append(exc)

        # Compensation logic
        if exceptions:
            if mongo_done and not postgres_done:
                # Rollback Mongo: restore original state
                collection.delete_many({"team_id": team_id})
                if original_mongo:
                    collection.insert_many(original_mongo)
            if postgres_done and not mongo_done:
                # Rollback Postgres: restore original state
                with transaction.atomic():
                    PostgresUserTeamDetails.objects.filter(team_id=team_id).delete()
                    for orig in original_postgres:
                        orig.pk = None  # To force insert
                        orig.save()
            raise Exception(f"Update team members failed: {exceptions}")

        return mongo_done and postgres_done
