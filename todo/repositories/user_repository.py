from datetime import datetime, timezone
from typing import Optional, List
from pymongo.collection import ReturnDocument
from pymongo import ASCENDING

from todo.models.user import UserModel
from todo.models.common.pyobjectid import PyObjectId
from todo_project.db.config import DatabaseManager
from todo.constants.messages import RepositoryErrors
from todo.exceptions.auth_exceptions import UserNotFoundException, APIException
import uuid
from todo.models.postgres.user import User as PostgresUser
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED,wait
from todo.utils.retry_utils import retry

class UserRepository:
    @classmethod
    def _get_collection(cls):
        return DatabaseManager().get_collection("users")

    @classmethod
    def _get_client(cls):
        return DatabaseManager()._database_client

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[UserModel]:
        try:
            collection = cls._get_collection()
            object_id = PyObjectId(user_id)
            doc = collection.find_one({"_id": object_id})
            return UserModel(**doc) if doc else None
        except Exception as e:
            raise UserNotFoundException() from e

    @classmethod
    def get_by_ids(cls, user_ids: List[str]) -> List[UserModel]:
        """
        Get multiple users by their IDs in a single database query.
        Returns only the users that exist.
        """
        try:
            if not user_ids:
                return []

            collection = cls._get_collection()
            object_ids = [PyObjectId(user_id) for user_id in user_ids]
            cursor = collection.find({"_id": {"$in": object_ids}})
            return [UserModel(**doc) for doc in cursor]
        except Exception as e:
            raise UserNotFoundException() from e

    @classmethod
    def create_or_update(cls, user_data: dict) -> UserModel:
        try:
            collection = cls._get_collection()
            now = datetime.now(timezone.utc)
            google_id = user_data["google_id"]

            try:
                existing_user = PostgresUser.objects.get(google_id=google_id)
                user_id = str(existing_user.id)
            except PostgresUser.DoesNotExist:
                user_id = str(uuid.uuid4())

            result = collection.find_one_and_update(
                {"google_id": google_id},
                {
                    "$set": {
                        "email_id": user_data["email"],
                        "name": user_data["name"],
                        "picture": user_data.get("picture"),
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "_id": user_id,
                        "google_id": google_id,
                        "created_at": now,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )

            if not result:
                print("[ERROR] No result returned from find_one_and_update")
                raise APIException(RepositoryErrors.USER_OPERATION_FAILED)

            try:
                PostgresUser.objects.update_or_create(
                    id=user_id,
                    defaults={
                        "google_id": result["google_id"],
                        "email_id": result["email_id"],
                        "name": result["name"],
                        "picture": result.get("picture"),
                    },
                )
            except Exception as orm_exc:
                if user_id:
                    collection.delete_one({"_id": user_id})
                print(
                    f"[ERROR] Postgres upsert failed for user_id: {user_id}, rolled back MongoDB insert/update, error: {orm_exc}"
                )
                raise
            return UserModel(**result)

        except Exception as e:
            if isinstance(e, APIException):
                raise
            raise APIException(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(str(e)))

    @classmethod
    def search_users(cls, query: str, page: int = 1, limit: int = 10) -> tuple[List[UserModel], int]:
        """
        Search users by name or email using fuzzy search with MongoDB regex
        """

        collection = cls._get_collection()
        regex_pattern = {"$regex": query, "$options": "i"}
        search_filter = {"$or": [{"name": regex_pattern}, {"email_id": regex_pattern}]}
        skip = (page - 1) * limit
        total_count = collection.count_documents(search_filter)
        cursor = collection.find(search_filter).sort("name", ASCENDING).skip(skip).limit(limit)
        users = [UserModel(**doc) for doc in cursor]
        return users, total_count

    @classmethod
    def get_all_users(cls, page: int = 1, limit: int = 10) -> tuple[List[UserModel], int]:
        """
        Get all users with pagination
        """
        collection = cls._get_collection()
        skip = (page - 1) * limit
        total_count = collection.count_documents({})
        cursor = collection.find().sort("name", ASCENDING).skip(skip).limit(limit)
        users = [UserModel(**doc) for doc in cursor]
        return users, total_count

    @classmethod
    def create_or_update_parallel(cls, user_data: dict) -> dict:
        collection = cls._get_collection()
        now = datetime.now(timezone.utc)
        google_id = user_data["google_id"]

        try:
            existing_user = PostgresUser.objects.get(google_id=google_id)
            user_id = str(existing_user.id)
        except PostgresUser.DoesNotExist:
            user_id = str(uuid.uuid4())

        def write_mongo():
            session = cls._get_client().start_session()
            with session.start_transaction():
                result = collection.find_one_and_update(
                    {"google_id": google_id},
                    {
                        "$set": {
                            "email_id": user_data["email"],
                            "name": user_data["name"],
                            "picture": user_data.get("picture"),
                            "updated_at": now,
                        },
                        "$setOnInsert": {
                            "_id": user_id,
                            "google_id": google_id,
                            "created_at": now,
                        },
                    },
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if not result:
                    raise APIException(RepositoryErrors.USER_OPERATION_FAILED)
                return result

        def write_postgres():
            with transaction.atomic():
                PostgresUser.objects.update_or_create(
                    id=user_id,
                    defaults={
                        "google_id": google_id,
                        "email_id": user_data["email"],
                        "name": user_data["name"],
                        "picture": user_data.get("picture"),
                    },
                )
            return "postgres_success"

        exceptions = []
        mongo_result = None
        postgres_done = False

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if isinstance(res, dict):
                        mongo_result = res
                    else:
                        postgres_done = True
                except Exception as exc:
                    exceptions.append(exc)
                    print(f"[ERROR] Write failed: {exc}")
        if exceptions:
            if mongo_result and not postgres_done:
                collection.delete_one({"_id": user_id})
                print(f"[COMPENSATION] Rolled back Mongo for user {user_id}")
            if postgres_done and not mongo_result:
                with transaction.atomic():
                    PostgresUser.objects.filter(id=user_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for user {user_id}")

            raise APIException(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(exceptions))

        user_model = UserModel(**mongo_result)
        return user_model