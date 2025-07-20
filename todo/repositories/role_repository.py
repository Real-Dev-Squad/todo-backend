from bson.errors import InvalidId
from typing import List, Dict, Any, Optional
from bson import ObjectId
import logging

from todo.models.role import RoleModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.role import RoleScope

logger = logging.getLogger(__name__)


class RoleRepository(MongoRepository):
    collection_name = RoleModel.collection_name

    @classmethod
    def list_all(cls, filters: Optional[Dict[str, Any]] = None) -> List[RoleModel]:
        roles_collection = cls.get_collection()

        query = {}
        if filters:
            if "is_active" in filters:
                query["is_active"] = filters["is_active"]
            if "name" in filters:
                query["name"] = filters["name"]
            if "scope" in filters:
                query["scope"] = filters["scope"]

        roles_cursor = roles_collection.find(query)
        roles = []

        for role_doc in roles_cursor:
            try:
                role_model = cls._document_to_model(role_doc)
                roles.append(role_model)
            except Exception as e:
                logger.error(f"Error converting role document to model: {e}")
                logger.error(f"Document: {role_doc}")
                continue

        return roles

    @classmethod
    def _document_to_model(cls, role_doc: dict) -> RoleModel:
        if "scope" in role_doc and isinstance(role_doc["scope"], str):
            role_doc["scope"] = RoleScope(role_doc["scope"])

        return RoleModel(**role_doc)

    @classmethod
    def get_by_id(cls, role_id: str) -> Optional[RoleModel]:
        roles_collection = cls.get_collection()
        role_data = roles_collection.find_one({"_id": ObjectId(role_id)})
        if role_data:
            return cls._document_to_model(role_data)
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional[RoleModel]:
        roles_collection = cls.get_collection()
        role_data = roles_collection.find_one({"name": name})
        if role_data:
            return cls._document_to_model(role_data)
        return None

    @classmethod
    def get_by_name_and_scope(cls, name: str, scope: str) -> Optional[RoleModel]:
        roles_collection = cls.get_collection()
        role_data = roles_collection.find_one({"name": name, "scope": scope})
        if role_data:
            return cls._document_to_model(role_data)
        return None
