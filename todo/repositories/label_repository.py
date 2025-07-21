from typing import List, Tuple
import re

from todo.models.label import LabelModel
from todo.repositories.common.mongo_repository import MongoRepository


class LabelRepository(MongoRepository):
    collection_name = LabelModel.collection_name

    @classmethod
    def list_by_ids(cls, ids: List[str]) -> List[LabelModel]:
        if len(ids) == 0:
            return []
        labels_collection = cls.get_collection()
        labels_cursor = labels_collection.find({"_id": {"$in": ids}})
        return [LabelModel(**label) for label in labels_cursor]

    @classmethod
    def get_all(cls, page, limit, search) -> Tuple[int, List[LabelModel]]:
        """
        Get paginated list of labels with optional search on name.
        """
        labels_collection = cls.get_collection()

        query = {"isDeleted": {"$ne": True}}

        if search:
            escaped_search = re.escape(search)
            query["name"] = {"$regex": escaped_search, "$options": "i"}

        zero_indexed_page = page - 1
        skip = zero_indexed_page * limit

        pipeline = [
            {"$match": query},
            {
                "$facet": {
                    "total": [{"$count": "count"}],
                    "data": [{"$sort": {"name": 1}}, {"$skip": skip}, {"$limit": limit}],
                }
            },
        ]

        aggregation_result = labels_collection.aggregate(pipeline)
        result = next(aggregation_result, {"total": [], "data": []})

        total_docs = result.get("total", [])
        total_count = total_docs[0].get("count", 0) if total_docs else 0

        labels = [LabelModel(**doc) for doc in result.get("data", [])]

        return total_count, labels
