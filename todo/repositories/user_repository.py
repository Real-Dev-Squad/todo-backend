from datetime import datetime, timezone
from typing import Optional

from todo.models.user import UserModel
from todo.models.common.pyobjectid import PyObjectId
from todo_project.db.config import DatabaseManager
from todo.constants.messages import RepositoryErrors
from todo.exceptions.google_auth_exceptions import GoogleUserNotFoundException, GoogleAPIException


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
        except Exception:
            raise GoogleUserNotFoundException()

    @classmethod
    def create_or_update(cls, user_data: dict) -> UserModel:
        try:
            collection = cls._get_collection()
            now = datetime.now(timezone.utc)
            google_id = user_data["google_id"]

            result = collection.find_one_and_update(
                {"googleId": google_id},
                {
                    "$set": {
                        "emailId": user_data["email"],
                        "name": user_data["name"],
                        "updatedAt": now,
                        "lastLoginAt": now,
                    },
                    "$setOnInsert": {"googleId": google_id, "createdAt": now},
                },
                upsert=True,
                return_document=True,
            )

            if not result:
                raise GoogleAPIException(RepositoryErrors.USER_OPERATION_FAILED)

            return UserModel(**result)

        except Exception as e:
            if isinstance(e, GoogleAPIException):
                raise
            raise GoogleAPIException(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(str(e)))
