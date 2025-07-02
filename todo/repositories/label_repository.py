from typing import List, Tuple
from pymongo import ASCENDING
from bson import ObjectId
import re

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

    @classmethod
    def get_all(cls, page, limit, search) -> Tuple[int, List[LabelModel]]:
        """
        Get paginated list of labels with optional search on name.

        Args:
            page (int): Page number (default: 1)
            limit (int): Number of items per page (default: 10)
            search (str): Search term for label name

        Returns:
            Tuple[int, List[LabelModel]]: Total count and paginated label list
        """
        labels_collection = cls.get_collection()

        query = {"isDeleted": {"$ne": True}}

        if search:
            escaped_search = re.escape(search)
            query["name"] = {"$regex": escaped_search, "$options": "i"}

        total_count = labels_collection.count_documents(query)

        zero_indexed_page = int(page) - 1
        skip = zero_indexed_page * limit

        labels_cursor = labels_collection.find(query).sort("name", ASCENDING).skip(skip).limit(limit)
        labels = [LabelModel(**label) for label in labels_cursor]

        return total_count, labels
