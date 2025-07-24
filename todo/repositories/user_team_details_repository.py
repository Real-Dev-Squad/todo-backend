from bson import ObjectId
from todo.repositories.common.mongo_repository import MongoRepository

class UserTeamDetailsRepository(MongoRepository):
    collection_name = "user_team_details"

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
            print(f"DEBUG: Trying user_team_details delete query: {query}")
            result = collection.delete_one(query)
            print(f"DEBUG: delete_one result: deleted={result.deleted_count}")
            if result.deleted_count > 0:
                return True
        return False 