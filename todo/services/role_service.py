from typing import List, Dict, Any, Optional

from todo.models.role import RoleModel
from todo.repositories.role_repository import RoleRepository
from todo.dto.role_dto import RoleDTO
from todo.exceptions.role_exceptions import (
    RoleNotFoundException,
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
