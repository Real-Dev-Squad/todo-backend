from datetime import datetime, timezone
from typing import List, Optional
import logging
from bson import ObjectId

from todo.models.user_role import UserRoleModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.role import RoleScope, RoleName
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService

logger = logging.getLogger(__name__)


class UserRoleRepository(MongoRepository):
    collection_name = UserRoleModel.collection_name

    @classmethod
    def create(cls, user_role: UserRoleModel) -> UserRoleModel:
        collection = cls.get_collection()

        role_name_value = user_role.role_name.value if hasattr(user_role.role_name, "value") else user_role.role_name
        scope_value = user_role.scope.value if hasattr(user_role.scope, "value") else user_role.scope

        # Check if already exists and is active
        existing = collection.find_one(
            {
                "user_id": user_role.user_id,
                "role_name": role_name_value,
                "scope": scope_value,
                "team_id": user_role.team_id,
                "is_active": True,
            }
        )

        if existing:
            return UserRoleModel(**existing)

        user_role.created_at = datetime.now(timezone.utc)
        user_role_dict = user_role.model_dump(mode="json", by_alias=True, exclude_none=True)
        result = collection.insert_one(user_role_dict)
        user_role.id = result.inserted_id

        dual_write_service = EnhancedDualWriteService()
        user_role_data = {
            "user_id": user_role.user_id,
            "role_name": user_role.role_name.value if hasattr(user_role.role_name, "value") else user_role.role_name,
            "scope": user_role.scope.value if hasattr(user_role.scope, "value") else user_role.scope,
            "team_id": user_role.team_id,
            "is_active": user_role.is_active,
            "created_at": user_role.created_at,
            "created_by": user_role.created_by,
        }

        dual_write_success = dual_write_service.create_document(
            collection_name="user_roles", data=user_role_data, mongo_id=str(user_role.id)
        )

        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync user role {user_role.id} to Postgres")

        return user_role

    @classmethod
    def get_user_roles(
        cls, user_id: Optional[str] = None, scope: Optional["RoleScope"] = None, team_id: Optional[str] = None
    ) -> List[UserRoleModel]:
        collection = cls.get_collection()

        query = {"is_active": True}

        if user_id:
            query["user_id"] = user_id

        if scope:
            scope_value = scope.value if hasattr(scope, "value") else scope
            query["scope"] = scope_value

        if team_id:
            query["team_id"] = team_id
        elif scope and (scope.value if hasattr(scope, "value") else scope) == "GLOBAL":
            query["team_id"] = None

        roles = []
        for doc in collection.find(query):
            roles.append(UserRoleModel(**doc))
        return roles

    @classmethod
    def get_by_user_role_scope_team(cls, user_id: str, role_id: str, scope: str, team_id: Optional[str] = None):
        collection = cls.get_collection()

        try:
            object_id = ObjectId(role_id)
        except Exception:
            return None

        query = {"_id": object_id, "user_id": user_id, "scope": scope, "is_active": True}

        if scope == "TEAM" and team_id:
            query["team_id"] = team_id
        elif scope == "GLOBAL":
            query["team_id"] = None

        result = collection.find_one(query)
        if result:
            return UserRoleModel(**result)
        return None

    @classmethod
    def assign_role(
        cls, user_id: str, role_name: "RoleName", scope: "RoleScope", team_id: Optional[str] = None
    ) -> UserRoleModel:
        """Assign a role to a user - simple and clean."""
        user_role = UserRoleModel(user_id=user_id, role_name=role_name, scope=scope, team_id=team_id, is_active=True)
        return cls.create(user_role)

    @classmethod
    def remove_role_by_id(cls, user_id: str, role_id: str, scope: str, team_id: Optional[str] = None) -> bool:
        """Remove a role from a user by role_id - simple deactivation."""
        collection = cls.get_collection()

        try:
            object_id = ObjectId(role_id)
        except Exception:
            return False

        query = {"_id": object_id, "user_id": user_id, "scope": scope, "is_active": True}

        if scope == "TEAM" and team_id:
            query["team_id"] = team_id
        elif scope == "GLOBAL":
            query["team_id"] = None

        current_role = collection.find_one(query)
        if not current_role:
            return False

        result = collection.update_one(query, {"$set": {"is_active": False}})

        if result.modified_count > 0:
            dual_write_service = EnhancedDualWriteService()
            user_role_data = {
                "user_id": str(current_role["user_id"]),
                "role_name": current_role["role_name"],
                "scope": current_role["scope"],
                "team_id": str(current_role["team_id"]) if current_role.get("team_id") else None,
                "is_active": False,
                "created_at": current_role["created_at"],
                "created_by": str(current_role["created_by"]),
            }

            dual_write_success = dual_write_service.update_document(
                collection_name="user_roles", data=user_role_data, mongo_id=str(current_role["_id"])
            )

            if not dual_write_success:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to sync user role removal {current_role['_id']} to Postgres")

        return result.modified_count > 0
