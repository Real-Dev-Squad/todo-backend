from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from todo.models.role import RoleModel
from todo.repositories.role_repository import RoleRepository
from todo.constants.role import RoleType, RoleScope
from todo.dto.role_dto import RoleDTO
from todo.exceptions.role_exceptions import (
    RoleNotFoundException,
    RoleAlreadyExistsException,
    RoleOperationException,
)


class RoleService:
    @classmethod
    def get_all_roles(cls, filters: Optional[Dict[str, Any]] = None) -> List[RoleDTO]:
        try:
            role_models = RoleRepository.list_all(filters=filters)
            return [RoleDTO.from_model(role) for role in role_models]
        except Exception as e:
            raise RoleOperationException(f"Failed to get roles: {str(e)}")

    @classmethod
    def get_role_by_id(cls, role_id: str) -> RoleDTO:
        role_model = RoleRepository.get_by_id(role_id)
        if not role_model:
            raise RoleNotFoundException(role_id)
        return RoleDTO.from_model(role_model)

    @classmethod
    def create_role(
        cls,
        name: str,
        description: Optional[str],
        role_type: str,
        scope: str,
        is_active: bool,
        created_by: str,
    ) -> RoleDTO:
        try:
            role_model = RoleModel(
                name=name,
                description=description,
                type=RoleType(role_type),
                scope=RoleScope(scope),
                is_active=is_active,
                created_by=created_by,
                created_at=datetime.now(timezone.utc),
            )

            created_role = RoleRepository.create(role_model)
            return RoleDTO.from_model(created_role)

        except ValueError as e:
            raise RoleAlreadyExistsException(str(e))
        except Exception as e:
            raise RoleOperationException(f"Failed to create role: {str(e)}")

    @classmethod
    def update_role(cls, role_id: str, **update_data) -> RoleDTO:
        try:
            existing_role = RoleRepository.get_by_id(role_id)
            if not existing_role:
                raise RoleNotFoundException(role_id)

            clean_update_data = {k: v for k, v in update_data.items() if v is not None}

            updated_role = RoleRepository.update(role_id, clean_update_data)
            if not updated_role:
                raise RoleOperationException(f"Failed to update role with ID: {role_id}")

            return RoleDTO.from_model(updated_role)

        except ValueError as e:
            raise RoleAlreadyExistsException(str(e))
        except RoleNotFoundException:
            raise
        except Exception as e:
            raise RoleOperationException(f"Failed to update role: {str(e)}")

    @classmethod
    def delete_role(cls, role_id: str) -> None:
        try:
            existing_role = RoleRepository.get_by_id(role_id)
            if not existing_role:
                raise RoleNotFoundException(role_id)

            success = RoleRepository.delete_by_id(role_id)
            if not success:
                raise RoleOperationException(f"Failed to delete role with ID: {role_id}")

        except RoleNotFoundException:
            raise
        except Exception as e:
            raise RoleOperationException(f"Failed to delete role: {str(e)}")
