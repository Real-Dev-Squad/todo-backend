from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pymongo import ReturnDocument
import logging

from todo.models.role import RoleModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.role import RoleScope
from todo.exceptions.role_exceptions import RoleAlreadyExistsException

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
    def create(cls, role: RoleModel) -> RoleModel:
        roles_collection = cls.get_collection()

        scope_value = role.scope.value if isinstance(role.scope, RoleScope) else role.scope
        existing_role = roles_collection.find_one({"name": role.name, "scope": scope_value})
        if existing_role:
            raise RoleAlreadyExistsException(role.name)

        role.created_at = datetime.now(timezone.utc)
        role.updated_at = None

        role_dict = role.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = roles_collection.insert_one(role_dict)

        role.id = insert_result.inserted_id
        return role

    @classmethod
    def get_by_id(cls, role_id: str) -> Optional[RoleModel]:
        roles_collection = cls.get_collection()
        role_data = roles_collection.find_one({"_id": role_id})
        if role_data:
            return cls._document_to_model(role_data)
        return None

    @classmethod
    def update(cls, role_id: str, update_data: dict) -> Optional[RoleModel]:
        if "name" in update_data:
            scope_value = update_data.get("scope", "GLOBAL")
            if isinstance(scope_value, RoleScope):
                scope_value = scope_value.value

            existing_role = cls.get_by_name_and_scope(update_data["name"], scope_value)
            if existing_role and str(existing_role.id) != role_id:
                raise RoleAlreadyExistsException(update_data["name"])

        if "scope" in update_data and isinstance(update_data["scope"], RoleScope):
            update_data["scope"] = update_data["scope"].value

        update_data["updated_at"] = datetime.now(timezone.utc)

        update_data.pop("_id", None)
        update_data.pop("id", None)

        roles_collection = cls.get_collection()
        updated_role_doc = roles_collection.find_one_and_update(
            {"_id": role_id}, {"$set": update_data}, return_document=ReturnDocument.AFTER
        )

        if updated_role_doc:
            return cls._document_to_model(updated_role_doc)
        return None

    @classmethod
    def delete_by_id(cls, role_id: str) -> bool:
        roles_collection = cls.get_collection()
        result = roles_collection.delete_one({"_id": role_id})
        return result.deleted_count > 0

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
