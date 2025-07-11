from bson.errors import InvalidId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import ReturnDocument

from todo.models.role import RoleModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.role import RoleType, RoleScope

class RoleRepository(MongoRepository):
    collection_name = RoleModel.collection_name

    @classmethod
    def list_all(cls, filters: Optional[Dict[str, Any]] = None) -> List[RoleModel]:
        roles_collection = cls.get_collection()

        query = {}
        if filters:
            if "is_active" in filters:
                query["is_active"] = filters["is_active"]
            if "type" in filters:
                query["type"] = filters["type"]
            if "scope" in filters:
                query["scope"] = filters["scope"]

        roles_cursor = roles_collection.find(query)
        roles = []
        
        for role_doc in roles_cursor:
            try:
                role_model = cls._document_to_model(role_doc)
                roles.append(role_model)
            except Exception as e:
                # Log the error and skip this document
                print(f"Error converting role document to model: {e}")
                print(f"Document: {role_doc}")
                continue
        
        return roles

    @classmethod
    def _document_to_model(cls, role_doc: dict) -> RoleModel:
        if "type" in role_doc and isinstance(role_doc["type"], str):
            role_doc["type"] = RoleType(role_doc["type"])
        
        if "scope" in role_doc and isinstance(role_doc["scope"], str):
            role_doc["scope"] = RoleScope(role_doc["scope"])
        
        return RoleModel(**role_doc)

    @classmethod
    def create(cls, role: RoleModel) -> RoleModel:
        roles_collection = cls.get_collection()

        existing_role = roles_collection.find_one({"name": role.name})
        if existing_role:
            raise ValueError(f"Role with name '{role.name}' already exists")

        role.created_at = datetime.now(timezone.utc)
        role.updated_at = None

        role_dict = role.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = roles_collection.insert_one(role_dict)

        role.id = insert_result.inserted_id
        return role

    @classmethod
    def get_by_id(cls, role_id: str) -> Optional[RoleModel]:
        roles_collection = cls.get_collection()
        role_data = roles_collection.find_one({"_id": ObjectId(role_id)})
        if role_data:
            return cls._document_to_model(role_data)
        return None

    @classmethod
    def update(cls, role_id: str, update_data: dict) -> Optional[RoleModel]:
        try:
            obj_id = ObjectId(role_id)
        except InvalidId:
            return None

        if "name" in update_data:
            existing_role = cls.get_by_name(update_data["name"])
            if existing_role and str(existing_role.id) != role_id:
                raise ValueError(f"Role with name '{update_data['name']}' already exists")

        update_data["updated_at"] = datetime.now(timezone.utc)

        update_data.pop("_id", None)
        update_data.pop("id", None)

        roles_collection = cls.get_collection()
        updated_role_doc = roles_collection.find_one_and_update(
            {"_id": obj_id}, {"$set": update_data}, return_document=ReturnDocument.AFTER
        )

        if updated_role_doc:
            return cls._document_to_model(updated_role_doc)
        return None

    @classmethod
    def delete_by_id(cls, role_id: str) -> bool:
        try:
            obj_id = ObjectId(role_id)
        except Exception:
            return False

        roles_collection = cls.get_collection()
        result = roles_collection.delete_one({"_id": obj_id})
        return result.deleted_count > 0

    @classmethod
    def get_by_name(cls, name: str) -> Optional[RoleModel]:
        roles_collection = cls.get_collection()
        role_data = roles_collection.find_one({"name": name})
        if role_data:
            return cls._document_to_model(role_data)
        return None
