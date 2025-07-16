from datetime import datetime, timezone
from typing import Optional, List
from pymongo.collection import ReturnDocument
from pymongo import ASCENDING

from todo.models.user import UserModel
from todo.models.common.pyobjectid import PyObjectId
from todo_project.db.config import DatabaseManager
from todo.constants.messages import RepositoryErrors
from todo.exceptions.auth_exceptions import UserNotFoundException, APIException


class UserRepository:
    @classmethod
    def _get_collection(cls):
        return DatabaseManager().get_collection("users")

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

            result = collection.find_one_and_update(
                {"google_id": google_id},
                {
                    "$set": {
                        "email_id": user_data["email"],
                        "name": user_data["name"],
                        "picture": user_data.get("picture"),
                        "updated_at": now,
                    },
                    "$setOnInsert": {"google_id": google_id, "created_at": now},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )

            if not result:
                raise APIException(RepositoryErrors.USER_OPERATION_FAILED)

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
