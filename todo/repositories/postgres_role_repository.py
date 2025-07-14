from datetime import datetime, timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from todo.models import Role, RoleScope


class RoleRepository:
    @classmethod
    def get_by_id(cls, role_id: str) -> Optional[Role]:
        try:
            return Role.objects.get(id=role_id)
        except (ObjectDoesNotExist, ValueError):
            return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional[Role]:
        try:
            return Role.objects.get(name=name)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def create(cls, role_data: dict) -> Role:
        try:
            with transaction.atomic():
                role = Role.objects.create(
                    name=role_data['name'],
                    description=role_data.get('description'),
                    scope=role_data.get('scope', RoleScope.GLOBAL),
                    is_active=role_data.get('is_active', True),
                    created_by=role_data['created_by'],
                    updated_by=role_data.get('updated_by'),
                )
                
                return role
                
        except Exception as e:
            raise Exception(f"Error creating role: {str(e)}")

    @classmethod
    def update(cls, role_id: str, update_data: dict) -> Optional[Role]:
        try:
            with transaction.atomic():
                role = cls.get_by_id(role_id)
                if not role:
                    return None
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(role, field):
                        setattr(role, field, value)
                
                role.updated_at = datetime.now(timezone.utc)
                role.save()
                
                return role
                
        except Exception as e:
            raise Exception(f"Error updating role: {str(e)}")

    @classmethod
    def delete(cls, role_id: str) -> bool:
        try:
            role = cls.get_by_id(role_id)
            if not role:
                return False
            
            role.is_active = False
            role.save()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting role: {str(e)}")

    @classmethod
    def get_all_active(cls) -> List[Role]:
        try:
            return list(Role.objects.filter(is_active=True))
        except Exception as e:
            raise Exception(f"Error getting all active roles: {str(e)}")

    @classmethod
    def get_by_scope(cls, scope: str) -> List[Role]:
        try:
            return list(Role.objects.filter(scope=scope, is_active=True))
        except Exception as e:
            raise Exception(f"Error getting roles by scope: {str(e)}")

    @classmethod
    def search_roles(cls, query: str, page: int = 1, limit: int = 10) -> tuple[List[Role], int]:
        """
        Search roles by name or description
        """
        try:
            from django.db.models import Q
            
            # Create filter for case-insensitive search
            search_filter = (
                Q(name__icontains=query) | Q(description__icontains=query)
            ) & Q(is_active=True)
            
            # Get total count
            total_count = Role.objects.filter(search_filter).count()
            
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get paginated results
            roles = Role.objects.filter(search_filter).order_by('name')[offset:offset + limit]
            
            return list(roles), total_count
            
        except Exception as e:
            raise Exception(f"Error searching roles: {str(e)}")
