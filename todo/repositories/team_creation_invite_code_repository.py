from typing import Optional, List
from datetime import datetime, timezone

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.team_creation_invite_code import TeamCreationInviteCodeModel
from todo.repositories.user_repository import UserRepository
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService


class TeamCreationInviteCodeRepository(MongoRepository):
    """Repository for team creation invite code operations."""

    collection_name = TeamCreationInviteCodeModel.collection_name

    @classmethod
    def is_code_valid(cls, code: str) -> Optional[dict]:
        """Check if a code is available for use (unused)."""
        collection = cls.get_collection()
        try:
            code_data = collection.find_one({"code": code, "is_used": False})
            return code_data
        except Exception as e:
            raise Exception(f"Error checking if code is valid: {e}")

    @classmethod
    def validate_and_consume_code(cls, code: str, used_by: str) -> Optional[dict]:
        """Validate and consume a code in one atomic operation using findOneAndUpdate."""
        collection = cls.get_collection()
        try:
            current_time = datetime.now(timezone.utc)
            result = collection.find_one_and_update(
                {"code": code, "is_used": False},
                {"$set": {"is_used": True, "used_by": used_by, "used_at": current_time.isoformat()}},
                return_document=True,
            )

            if result:
                # Sync the update to PostgreSQL
                dual_write_service = EnhancedDualWriteService()
                invite_code_data = {
                    "code": result["code"],
                    "description": result.get("description"),
                    "is_used": True,
                    "created_by": str(result["created_by"]),
                    "used_by": str(used_by),
                    "created_at": result.get("created_at"),
                    "used_at": current_time,
                }

                dual_write_success = dual_write_service.update_document(
                    collection_name="team_creation_invite_codes", data=invite_code_data, mongo_id=str(result["_id"])
                )

                if not dual_write_success:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync team creation invite code update {result['_id']} to Postgres")

            return result
        except Exception as e:
            raise Exception(f"Error validating and consuming code: {e}")

    @classmethod
    def create(cls, team_invite_code: TeamCreationInviteCodeModel) -> TeamCreationInviteCodeModel:
        collection = cls.get_collection()
        team_invite_code.created_at = datetime.now(timezone.utc)

        code_dict = team_invite_code.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(code_dict)
        team_invite_code.id = insert_result.inserted_id

        dual_write_service = EnhancedDualWriteService()
        invite_code_data = {
            "code": team_invite_code.code,
            "description": team_invite_code.description,
            "is_used": team_invite_code.is_used,
            "created_by": str(team_invite_code.created_by),
            "used_by": str(team_invite_code.used_by) if team_invite_code.used_by else None,
            "created_at": team_invite_code.created_at,
            "used_at": team_invite_code.used_at,
        }

        dual_write_success = dual_write_service.create_document(
            collection_name="team_creation_invite_codes", data=invite_code_data, mongo_id=str(team_invite_code.id)
        )

        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync team creation invite code {team_invite_code.id} to Postgres")

        return team_invite_code

    @classmethod
    def get_all_codes(cls, page: int = 1, limit: int = 10) -> tuple[List[dict], int]:
        """Get paginated team creation invite codes with user details for created_by and used_by."""
        collection = cls.get_collection()
        try:
            skip = (page - 1) * limit

            total_count = collection.count_documents({})

            codes = list(collection.find().sort("created_at", -1).skip(skip).limit(limit))

            enhanced_codes = []
            for code in codes:
                created_by_user = None
                used_by_user = None

                if code.get("created_by"):
                    user = UserRepository.get_by_id(str(code["created_by"]))
                    if user:
                        created_by_user = {"id": str(user.id), "name": user.name}

                if code.get("used_by"):
                    user = UserRepository.get_by_id(str(code["used_by"]))
                    if user:
                        used_by_user = {"id": str(user.id), "name": user.name}

                enhanced_code = {
                    "id": str(code["_id"]),
                    "code": code["code"],
                    "description": code.get("description"),
                    "created_at": code.get("created_at"),
                    "used_at": code.get("used_at"),
                    "is_used": code.get("is_used", False),
                    "created_by": created_by_user or {},
                    "used_by": used_by_user,
                }
                enhanced_codes.append(enhanced_code)

            return enhanced_codes, total_count
        except Exception as e:
            raise Exception(f"Error getting all codes with user details: {e}")
