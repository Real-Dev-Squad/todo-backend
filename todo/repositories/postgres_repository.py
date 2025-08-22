from typing import Any, Dict, List, Optional, Type
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from todo.repositories.abstract_repository import AbstractRepository
from todo.models.postgres import (
    PostgresUser,
    PostgresTask,
    PostgresTaskLabel,
    PostgresDeferredDetails,
    PostgresTeam,
    PostgresUserTeamDetails,
    PostgresLabel,
    PostgresRole,
    PostgresTaskAssignment,
    PostgresWatchlist,
    PostgresWatchlistTask,
    PostgresUserRole,
    PostgresAuditLog,
)


class BasePostgresRepository(AbstractRepository):
    """
    Base Postgres repository implementation.
    Provides common CRUD operations for Postgres models.
    """

    def __init__(self, model_class: Type[models.Model]):
        self.model_class = model_class

    def create(self, data: Dict[str, Any]) -> Any:
        """Create a new record in Postgres."""
        try:
            instance = self.model_class.objects.create(**data)
            return instance
        except Exception as e:
            raise Exception(f"Failed to create record: {str(e)}")

    def get_by_id(self, id: str) -> Optional[Any]:
        """Get a record by ID (using mongo_id field)."""
        try:
            return self.model_class.objects.get(mongo_id=id)
        except ObjectDoesNotExist:
            return None

    def get_all(self, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100) -> List[Any]:
        """Get all records with optional filtering and pagination."""
        queryset = self.model_class.objects.all()

        if filters:
            queryset = self._apply_filters(queryset, filters)

        return list(queryset[skip : skip + limit])

    def update(self, id: str, data: Dict[str, Any]) -> Optional[Any]:
        """Update a record by ID."""
        try:
            instance = self.model_class.objects.get(mongo_id=id)
            for field, value in data.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
            instance.save()
            return instance
        except ObjectDoesNotExist:
            return None

    def delete(self, id: str) -> bool:
        """Delete a record by ID."""
        try:
            instance = self.model_class.objects.get(mongo_id=id)
            instance.delete()
            return True
        except ObjectDoesNotExist:
            return False

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering."""
        queryset = self.model_class.objects.all()

        if filters:
            queryset = self._apply_filters(queryset, filters)

        return queryset.count()

    def exists(self, id: str) -> bool:
        """Check if a record exists by ID."""
        return self.model_class.objects.filter(mongo_id=id).exists()

    def _apply_filters(self, queryset, filters: Dict[str, Any]):
        """Apply filters to a queryset."""
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                if isinstance(value, dict):
                    # Handle complex filters like {'gte': value, 'lte': value}
                    for operator, operator_value in value.items():
                        if operator == "gte":
                            queryset = queryset.filter(**{f"{field}__gte": operator_value})
                        elif operator == "lte":
                            queryset = queryset.filter(**{f"{field}__lte": operator_value})
                        elif operator == "contains":
                            queryset = queryset.filter(**{f"{field}__icontains": operator_value})
                        elif operator == "in":
                            queryset = queryset.filter(**{f"{field}__in": operator_value})
                else:
                    queryset = queryset.filter(**{field: value})

        return queryset


class PostgresUserRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for user operations."""

    def __init__(self):
        super().__init__(PostgresUser)

    def get_by_email(self, email: str) -> Optional[PostgresUser]:
        """Get user by email address."""
        try:
            return PostgresUser.objects.get(email_id=email)
        except ObjectDoesNotExist:
            return None

    def get_by_google_id(self, google_id: str) -> Optional[PostgresUser]:
        """Get user by Google ID."""
        try:
            return PostgresUser.objects.get(google_id=google_id)
        except ObjectDoesNotExist:
            return None


class PostgresTaskRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for task operations."""

    def __init__(self):
        super().__init__(PostgresTask)

    def get_by_user(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100
    ) -> List[PostgresTask]:
        """Get tasks by user ID."""
        queryset = PostgresTask.objects.filter(created_by=user_id)

        if filters:
            queryset = self._apply_filters(queryset, filters)

        return list(queryset[skip : skip + limit])

    def get_by_team(
        self, team_id: str, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100
    ) -> List[PostgresTask]:
        """Get tasks by team ID."""
        # This would need to be implemented based on your team-task relationship
        # For now, returning empty list
        return []

    def get_by_status(
        self, status: str, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100
    ) -> List[PostgresTask]:
        """Get tasks by status."""
        queryset = PostgresTask.objects.filter(status=status)

        if filters:
            queryset = self._apply_filters(queryset, filters)

        return list(queryset[skip : skip + limit])

    def get_by_priority(
        self, priority: str, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100
    ) -> List[PostgresTask]:
        """Get tasks by priority."""
        queryset = PostgresTask.objects.filter(priority=priority)

        if filters:
            queryset = self._apply_filters(queryset, filters)

        return list(queryset[skip : skip + limit])


class PostgresTeamRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for team operations."""

    def __init__(self):
        super().__init__(PostgresTeam)

    def get_by_invite_code(self, invite_code: str) -> Optional[PostgresTeam]:
        """Get team by invite code."""
        try:
            return PostgresTeam.objects.get(invite_code=invite_code)
        except ObjectDoesNotExist:
            return None

    def get_by_user(self, user_id: str) -> List[PostgresTeam]:
        """Get teams by user ID."""
        # Get teams where user is a member
        user_teams = PostgresUserTeamDetails.objects.filter(user_id=user_id, is_active=True).values_list(
            "team_id", flat=True
        )

        return list(PostgresTeam.objects.filter(mongo_id__in=user_teams))


class PostgresLabelRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for label operations."""

    def __init__(self):
        super().__init__(PostgresLabel)

    def get_by_name(self, name: str) -> Optional[PostgresLabel]:
        """Get label by name."""
        try:
            return PostgresLabel.objects.get(name=name)
        except ObjectDoesNotExist:
            return None


class PostgresRoleRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for role operations."""

    def __init__(self):
        super().__init__(PostgresRole)

    def get_by_name(self, name: str) -> Optional[PostgresRole]:
        """Get role by name."""
        try:
            return PostgresRole.objects.get(name=name)
        except ObjectDoesNotExist:
            return None


class PostgresTaskAssignmentRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for task assignment operations."""

    def __init__(self):
        super().__init__(PostgresTaskAssignment)

    def get_by_task(self, task_id: str) -> List[PostgresTaskAssignment]:
        """Get assignments by task ID."""
        return list(PostgresTaskAssignment.objects.filter(task_mongo_id=task_id))

    def get_by_user(self, user_id: str) -> List[PostgresTaskAssignment]:
        """Get assignments by user ID."""
        return list(PostgresTaskAssignment.objects.filter(user_mongo_id=user_id))

    def get_by_team(self, team_id: str) -> List[PostgresTaskAssignment]:
        """Get assignments by team ID."""
        return list(PostgresTaskAssignment.objects.filter(team_mongo_id=team_id))


class PostgresWatchlistRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for watchlist operations."""

    def __init__(self):
        super().__init__(PostgresWatchlist)

    def get_by_user(self, user_id: str) -> List[PostgresWatchlist]:
        """Get watchlists by user ID."""
        return list(PostgresWatchlist.objects.filter(user_mongo_id=user_id))


class PostgresUserRoleRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for user role operations."""

    def __init__(self):
        super().__init__(PostgresUserRole)

    def get_by_user(self, user_id: str) -> List[PostgresUserRole]:
        """Get user roles by user ID."""
        return list(PostgresUserRole.objects.filter(user_mongo_id=user_id))

    def get_by_team(self, team_id: str) -> List[PostgresUserRole]:
        """Get user roles by team ID."""
        return list(PostgresUserRole.objects.filter(team_mongo_id=team_id))


class PostgresUserTeamDetailsRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for user team details operations."""

    def __init__(self):
        super().__init__(PostgresUserTeamDetails)

    def get_by_user(self, user_id: str) -> List[PostgresUserTeamDetails]:
        """Get user team details by user ID."""
        return list(PostgresUserTeamDetails.objects.filter(user_id=user_id))

    def get_by_team(self, team_id: str) -> List[PostgresUserTeamDetails]:
        """Get user team details by team ID."""
        return list(PostgresUserTeamDetails.objects.filter(team_id=team_id))


class PostgresAuditLogRepository(BasePostgresRepository, AbstractRepository):
    """Postgres repository for audit log operations."""

    def __init__(self):
        super().__init__(PostgresAuditLog)

    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[PostgresAuditLog]:
        """Get audit logs by user ID."""
        return list(PostgresAuditLog.objects.filter(user_mongo_id=user_id)[skip : skip + limit])

    def get_by_collection(self, collection_name: str, skip: int = 0, limit: int = 100) -> List[PostgresAuditLog]:
        """Get audit logs by collection name."""
        return list(PostgresAuditLog.objects.filter(collection_name=collection_name)[skip : skip + limit])

    def get_by_action(self, action: str, skip: int = 0, limit: int = 100) -> List[PostgresAuditLog]:
        """Get audit logs by action."""
        return list(PostgresAuditLog.objects.filter(action=action)[skip : skip + limit])
