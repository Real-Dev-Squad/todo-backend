from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from todo.models.role import RoleModel
from todo.repositories.role_repository import RoleRepository
from todo.constants.role import RoleScope
from todo.dto.role_dto import RoleDTO
from todo.exceptions.role_exceptions import (
    RoleNotFoundException,
    RoleAlreadyExistsException,
    RoleOperationException,
)


class RoleService:
    @classmethod
    def get_all_roles(cls, filters: Optional[Dict[str, Any]] = None) -> List[RoleDTO]:
        """Get all roles with optional filtering."""
        try:
            role_models = RoleRepository.list_all(filters=filters)
            return [RoleDTO.from_model(role) for role in role_models]
        except Exception as e:
            raise RoleOperationException(f"Failed to get roles: {str(e)}")

    @classmethod
    def get_role_by_id(cls, role_id: str) -> RoleDTO:
        """Get a single role by ID."""
        role_model = RoleRepository.get_by_id(role_id)
        if not role_model:
            raise RoleNotFoundException(role_id)
        return RoleDTO.from_model(role_model)

    @classmethod
    def create_role(
        cls,
        name: str,
        description: Optional[str],
        scope: str,
        is_active: bool,
        created_by: str,
    ) -> RoleDTO:
        """Create a new role."""
        try:
            role_model = RoleModel(
                name=name,
                description=description,
                scope=RoleScope(scope),
                is_active=is_active,
                created_by=created_by,
                created_at=datetime.now(timezone.utc),
            )

            created_role = RoleRepository.create(role_model)
            return RoleDTO.from_model(created_role)

        except RoleAlreadyExistsException:
            raise
        except ValueError as e:
            raise RoleOperationException(f"Invalid enum value: {str(e)}")
        except Exception as e:
            raise RoleOperationException(f"Failed to create role: {str(e)}")

    @classmethod
    def _transform_update_data(cls, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform and clean update data for role updates.

        Args:
            update_data: Raw update data from the view layer

        Returns:
            Dict[str, Any]: Cleaned and transformed update data

        Raises:
            ValueError: If enum conversion fails
        """
        clean_data = {k: v for k, v in update_data.items() if v is not None}

        if "scope" in clean_data and isinstance(clean_data["scope"], str):
            clean_data["scope"] = RoleScope(clean_data["scope"])

        return clean_data

    @classmethod
    def update_role(cls, role_id: str, **update_data) -> RoleDTO:
        """Update an existing role."""
        existing_role = RoleRepository.get_by_id(role_id)
        if not existing_role:
            raise RoleNotFoundException(role_id)

        try:
            clean_update_data = cls._transform_update_data(update_data)
            updated_role = RoleRepository.update(role_id, clean_update_data)

            if not updated_role:
                raise RoleOperationException(f"Failed to update role with ID: {role_id}")

            return RoleDTO.from_model(updated_role)

        except RoleAlreadyExistsException:
            raise
        except ValueError as e:
            raise RoleOperationException(f"Invalid enum value: {str(e)}")
        except Exception as e:
            raise RoleOperationException(f"Failed to update role: {str(e)}")

    @classmethod
    def delete_role(cls, role_id: str) -> None:
        """Delete a role by ID."""
        existing_role = RoleRepository.get_by_id(role_id)
        if not existing_role:
            raise RoleNotFoundException(role_id)

        try:
            success = RoleRepository.delete_by_id(role_id)
            if not success:
                raise RoleOperationException(f"Failed to delete role with ID: {role_id}")
        except Exception as e:
            raise RoleOperationException(f"Failed to delete role: {str(e)}")
