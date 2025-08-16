from typing import Optional
from bson import ObjectId
from datetime import datetime, timezone

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.team_invite_code import TeamInviteCodeModel


class TeamInviteCodeRepository(MongoRepository):
    """Repository for team invite code operations."""

    collection_name = TeamInviteCodeModel.collection_name

    @classmethod
    def consume_code(cls, code_id: ObjectId, used_by: str) -> bool:
        """Consume a valid code and mark it as used in one atomic operation."""
        collection = cls.get_collection()
        try:
            result = collection.update_one(
                {"_id": code_id, "is_used": False},
                {"$set": {"is_used": True, "used_by": ObjectId(used_by), "used_at": datetime.now(timezone.utc)}},
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error consuming code: {e}")

    @classmethod
    def is_code_valid(cls, code: str) -> Optional[TeamInviteCodeModel]:
        """Check if a code is available for use (unused)."""
        collection = cls.get_collection()
        try:
            code_data = collection.find_one({"code": code, "is_used": False})
            return code_data
        except Exception:
            return None

    @classmethod
    def create(cls, team_invite_code: TeamInviteCodeModel) -> TeamInviteCodeModel:
        """Create a new team invite code."""
        collection = cls.get_collection()
        team_invite_code.created_at = datetime.now(timezone.utc)

        code_dict = team_invite_code.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(code_dict)
        team_invite_code.id = insert_result.inserted_id
        return team_invite_code
