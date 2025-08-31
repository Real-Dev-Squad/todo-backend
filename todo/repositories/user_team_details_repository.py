from bson import ObjectId
from todo.repositories.common.mongo_repository import MongoRepository
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService


class UserTeamDetailsRepository(MongoRepository):
    collection_name = "user_team_details"

    @classmethod
    def get_by_user_and_team(cls, user_id: str, team_id: str):
        collection = cls.get_collection()
        try:
            user_id_obj = ObjectId(user_id)
        except Exception:
            user_id_obj = user_id
        try:
            team_id_obj = ObjectId(team_id)
        except Exception:
            team_id_obj = team_id

        queries = [
            {"user_id": user_id_obj, "team_id": team_id_obj},
            {"user_id": user_id, "team_id": team_id_obj},
            {"user_id": user_id_obj, "team_id": team_id},
            {"user_id": user_id, "team_id": team_id},
        ]

        for query in queries:
            result = collection.find_one(query)
            if result:
                return result
        return None

    @classmethod
    def remove_member_from_team(cls, user_id: str, team_id: str) -> bool:
        collection = cls.get_collection()
        try:
            user_id_obj = ObjectId(user_id)
        except Exception:
            user_id_obj = user_id
        try:
            team_id_obj = ObjectId(team_id)
        except Exception:
            team_id_obj = team_id
        queries = [
            {"user_id": user_id_obj, "team_id": team_id_obj},
            {"user_id": user_id, "team_id": team_id_obj},
            {"user_id": user_id_obj, "team_id": team_id},
            {"user_id": user_id, "team_id": team_id},
        ]
        for query in queries:
            document = collection.find_one(query)
            if document:
                result = collection.delete_one(query)
                if result.deleted_count > 0:
                    dual_write_service = EnhancedDualWriteService()
                    dual_write_success = dual_write_service.delete_document(
                        collection_name="user_team_details", mongo_id=str(document["_id"])
                    )

                    if not dual_write_success:
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to sync user team details deletion {document['_id']} to Postgres")

                    return True
        return False
