from typing import Optional

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.watchlist import WatchlistModel


class WatchlistRepository(MongoRepository):
    collection_name = WatchlistModel.collection_name

    @classmethod
    def get_by_user_and_task(cls, user_id: str, task_id: str) -> Optional[WatchlistModel]:
        doc = cls.get_collection().find_one({"userId": user_id, "taskId": task_id})
        return WatchlistModel(**doc) if doc else None

    @classmethod
    def create(cls, watchlist_model: WatchlistModel) -> WatchlistModel:
        doc = watchlist_model.model_dump(by_alias=True)
        doc.pop("_id", None)
        insert_result = cls.get_collection().insert_one(doc)
        watchlist_model.id = str(insert_result.inserted_id)
        return watchlist_model
