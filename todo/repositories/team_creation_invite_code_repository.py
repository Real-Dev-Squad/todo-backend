from typing import Optional
from bson import ObjectId
from datetime import datetime, timezone

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.team_creation_invite_code import TeamCreationInviteCodeModel


class TeamCreationInviteCodeRepository(MongoRepository):
    """Repository for team creation invite code operations."""

    collection_name = TeamCreationInviteCodeModel.collection_name

    @classmethod
    def consume_code(cls, code_id: ObjectId, used_by: str) -> bool:
        """Consume a valid code and mark it as used in one atomic operation."""
        collection = cls.get_collection()
        try:
            current_time = datetime.now(timezone.utc)
            result = collection.update_one(
                {"_id": code_id, "is_used": False},
                {"$set": {"is_used": True, "used_by": used_by, "used_at": current_time.isoformat()}},
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error consuming code: {e}")

    @classmethod
    def is_code_valid(cls, code: str) -> Optional[TeamCreationInviteCodeModel]:
        """Check if a code is available for use (unused)."""
        collection = cls.get_collection()
        try:
            code_data = collection.find_one({"code": code, "is_used": False})
            return code_data
        except Exception as e:
            raise Exception(f"Error checking if code is valid: {e}")

    @classmethod
    def create(cls, team_invite_code: TeamCreationInviteCodeModel) -> TeamCreationInviteCodeModel:
        """Create a new team invite code."""
        collection = cls.get_collection()
        team_invite_code.created_at = datetime.now(timezone.utc)

        code_dict = team_invite_code.model_dump(mode="json", by_alias=True, exclude_none=True)
        code_dict["created_at"] = team_invite_code.created_at.isoformat()
        insert_result = collection.insert_one(code_dict)
        team_invite_code.id = insert_result.inserted_id
        return team_invite_code
