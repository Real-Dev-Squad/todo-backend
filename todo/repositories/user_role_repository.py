from datetime import datetime, timezone
from typing import List, Optional
import logging

from todo.models.user_role import UserRoleModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.role import RoleScope, RoleName

logger = logging.getLogger(__name__)


class UserRoleRepository(MongoRepository):
    collection_name = UserRoleModel.collection_name

    @classmethod
    def create(cls, user_role: UserRoleModel) -> UserRoleModel:
        collection = cls.get_collection()
        
        # Check if already exists and is active
        existing = collection.find_one({
            "user_id": user_role.user_id,
            "role_name": user_role.role_name.value,  # Compare with enum value
            "scope": user_role.scope.value,
            "team_id": user_role.team_id,
            "is_active": True
        })
        
        if existing:
            return UserRoleModel(**existing)

        user_role.created_at = datetime.now(timezone.utc)
        user_role_dict = user_role.model_dump(mode="json", by_alias=True, exclude_none=True)
        result = collection.insert_one(user_role_dict)
        user_role.id = result.inserted_id
        return user_role

    @classmethod
    def get_user_roles(cls, user_id: str, scope: Optional['RoleScope'] = None, 
                      team_id: Optional[str] = None) -> List[UserRoleModel]:
        collection = cls.get_collection()
        
        query = {"user_id": user_id, "is_active": True}
        
        if scope:
            query["scope"] = scope.value
            
        if team_id:
            query["team_id"] = team_id
        elif scope and scope.value == "GLOBAL":
            query["team_id"] = None

        roles = []
        for doc in collection.find(query):
            roles.append(UserRoleModel(**doc))
        return roles

    @classmethod
    def assign_role(cls, user_id: str, role_name: 'RoleName', scope: 'RoleScope', 
                   team_id: Optional[str] = None) -> UserRoleModel:
        """Assign a role to a user - simple and clean."""
        user_role = UserRoleModel(
            user_id=user_id,
            role_name=role_name,
            scope=scope,
            team_id=team_id,
            is_active=True
        )
        return cls.create(user_role)

    @classmethod
    def remove_role(cls, user_id: str, role_name: 'RoleName', scope: 'RoleScope', 
                   team_id: Optional[str] = None) -> bool:
        """Remove a role from a user - simple deactivation."""
        collection = cls.get_collection()
        
        query = {
            "user_id": user_id,
            "role_name": role_name.value,
            "scope": scope.value,
            "is_active": True
        }
        
        if scope.value == "TEAM" and team_id:
            query["team_id"] = team_id
        elif scope.value == "GLOBAL":
            query["team_id"] = None

        result = collection.update_many(
            query,
            {"$set": {"is_active": False}}
        )
        
        return result.modified_count > 0 