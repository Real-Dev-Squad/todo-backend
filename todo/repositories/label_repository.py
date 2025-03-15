from typing import List

from bson import ObjectId
from todo.models.label import LabelModel
from todo.repositories.common.mongo_repository import MongoRepository


class LabelRepository(MongoRepository):
    collection_name = LabelModel.collection_name

    @classmethod
    def list_by_ids(cls, ids: List[ObjectId]) -> List[LabelModel]:
        if len(ids) == 0:
            return []
        labels_collection = cls.get_collection()
        labels_cursor = labels_collection.find({"_id": {"$in": ids}})
        return [LabelModel(**label) for label in labels_cursor]
