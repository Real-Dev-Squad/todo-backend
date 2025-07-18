from datetime import datetime, timezone
from typing import List, Tuple
from typing import Optional

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.watchlist import WatchlistModel
from todo.dto.watchlist_dto import WatchlistDTO
from bson import ObjectId


def _convert_objectids_to_str(obj):
    """Recursively convert all ObjectId values in a dict/list to strings."""
    if isinstance(obj, dict):
        return {k: _convert_objectids_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_objectids_to_str(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj


class WatchlistRepository(MongoRepository):
    collection_name = WatchlistModel.collection_name

    @classmethod
    def get_by_user_and_task(cls, user_id: str, task_id: str) -> Optional[WatchlistModel]:
        doc = cls.get_collection().find_one({"userId": user_id, "taskId": task_id})
        if doc:
            # Convert ObjectId fields to strings for the model
            if "updatedBy" in doc and doc["updatedBy"]:
                doc["updatedBy"] = str(doc["updatedBy"])
            return WatchlistModel(**doc)
        return None

    @classmethod
    def create(cls, watchlist_model: WatchlistModel) -> WatchlistModel:
        doc = watchlist_model.model_dump(by_alias=True)
        doc.pop("_id", None)
        insert_result = cls.get_collection().insert_one(doc)
        watchlist_model.id = str(insert_result.inserted_id)
        return watchlist_model

    @classmethod
    def get_watchlisted_tasks(cls, page, limit, user_id) -> Tuple[int, List[WatchlistDTO]]:
        """
        Get paginated list of watchlisted tasks.
        """
        watchlist_collection = cls.get_collection()

        query = {"userId": user_id, "isActive": True}

        zero_indexed_page = page - 1
        skip = zero_indexed_page * limit

        pipeline = [
            {"$match": query},
            {
                "$facet": {
                    "data": [
                        {
                            "$lookup": {
                                "from": "tasks",
                                "let": {"taskIdStr": "$taskId"},
                                "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", {"$toObjectId": "$$taskIdStr"}]}}}],
                                "as": "task",
                            }
                        },
                        {"$unwind": "$task"},
                        {
                            "$replaceRoot": {
                                "newRoot": {
                                    "$mergeObjects": [
                                        "$task",
                                        {"watchlistId": {"$toString": "$_id"}, "taskId": {"$toString": "$task._id"}},
                                    ]
                                }
                            }
                        },
                        {"$skip": skip},
                        {"$limit": limit},
                    ],
                    "total": [{"$count": "value"}],
                }
            },
            {"$addFields": {"total": {"$ifNull": [{"$arrayElemAt": ["$total.value", 0]}, 0]}}},
        ]

        aggregation_result = watchlist_collection.aggregate(pipeline)
        result = next(aggregation_result, {"total": 0, "data": []})
        count = result.get("total", 0)

        tasks = [_convert_objectids_to_str(doc) for doc in result.get("data", [])]
        tasks = [WatchlistDTO(**doc) for doc in tasks]

        return count, tasks

    @classmethod
    def update(cls, taskId: ObjectId, isActive: bool, userId: ObjectId) -> dict:
        """
        Update the watchlist status of a task.
        """
        watchlist_collection = cls.get_collection()
        update_result = watchlist_collection.update_one(
            {"userId": str(userId), "taskId": str(taskId)},
            {
                "$set": {
                    "isActive": isActive,
                    "updatedAt": datetime.now(timezone.utc),
                    "updatedBy": userId,
                }
            },
        )

        if update_result.modified_count == 0:
            return None
        return update_result
