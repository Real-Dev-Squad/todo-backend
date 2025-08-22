from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class AbstractRepository(ABC, Generic[T]):
    """
    Abstract repository interface that defines the contract for data access.
    This enables seamless switching between MongoDB and Postgres in the future.
    """
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """Create a new document/record."""
        pass
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """Get a document/record by ID."""
        pass
    
    @abstractmethod
    def get_all(self, filters: Optional[Dict[str, Any]] = None, 
                skip: int = 0, limit: int = 100) -> List[T]:
        """Get all documents/records with optional filtering and pagination."""
        pass
    
    @abstractmethod
    def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update a document/record by ID."""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a document/record by ID."""
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents/records with optional filtering."""
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """Check if a document/record exists by ID."""
        pass


class AbstractUserRepository(AbstractRepository[T]):
    """Abstract repository for user operations."""
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[T]:
        """Get user by email address."""
        pass
    
    @abstractmethod
    def get_by_google_id(self, google_id: str) -> Optional[T]:
        """Get user by Google ID."""
        pass


class AbstractTaskRepository(AbstractRepository[T]):
    """Abstract repository for task operations."""
    
    @abstractmethod
    def get_by_user(self, user_id: str, filters: Optional[Dict[str, Any]] = None,
                    skip: int = 0, limit: int = 100) -> List[T]:
        """Get tasks by user ID."""
        pass
    
    @abstractmethod
    def get_by_team(self, team_id: str, filters: Optional[Dict[str, Any]] = None,
                    skip: int = 0, limit: int = 100) -> List[T]:
        """Get tasks by team ID."""
        pass
    
    @abstractmethod
    def get_by_status(self, status: str, filters: Optional[Dict[str, Any]] = None,
                      skip: int = 0, limit: int = 100) -> List[T]:
        """Get tasks by status."""
        pass
    
    @abstractmethod
    def get_by_priority(self, priority: str, filters: Optional[Dict[str, Any]] = None,
                        skip: int = 0, limit: int = 100) -> List[T]:
        """Get tasks by priority."""
        pass


class AbstractTeamRepository(AbstractRepository[T]):
    """Abstract repository for team operations."""
    
    @abstractmethod
    def get_by_invite_code(self, invite_code: str) -> Optional[T]:
        """Get team by invite code."""
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[T]:
        """Get teams by user ID."""
        pass


class AbstractLabelRepository(AbstractRepository[T]):
    """Abstract repository for label operations."""
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[T]:
        """Get label by name."""
        pass


class AbstractRoleRepository(AbstractRepository[T]):
    """Abstract repository for role operations."""
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[T]:
        """Get role by name."""
        pass


class AbstractTaskAssignmentRepository(AbstractRepository[T]):
    """Abstract repository for task assignment operations."""
    
    @abstractmethod
    def get_by_task(self, task_id: str) -> List[T]:
        """Get assignments by task ID."""
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[T]:
        """Get assignments by user ID."""
        pass
    
    @abstractmethod
    def get_by_team(self, team_id: str) -> List[T]:
        """Get assignments by team ID."""
        pass


class AbstractWatchlistRepository(AbstractRepository[T]):
    """Abstract repository for watchlist operations."""
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[T]:
        """Get watchlists by user ID."""
        pass


class AbstractUserRoleRepository(AbstractRepository[T]):
    """Abstract repository for user role operations."""
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[T]:
        """Get user roles by user ID."""
        pass
    
    @abstractmethod
    def get_by_team(self, team_id: str) -> List[T]:
        """Get user roles by team ID."""
        pass


class AbstractUserTeamDetailsRepository(AbstractRepository[T]):
    """Abstract repository for user team details operations."""
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[T]:
        """Get user team details by user ID."""
        pass
    
    @abstractmethod
    def get_by_team(self, team_id: str) -> List[T]:
        """Get user team details by team ID."""
        pass


class AbstractAuditLogRepository(AbstractRepository[T]):
    """Abstract repository for audit log operations."""
    
    @abstractmethod
    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[T]:
        """Get audit logs by user ID."""
        pass
    
    @abstractmethod
    def get_by_collection(self, collection_name: str, skip: int = 0, limit: int = 100) -> List[T]:
        """Get audit logs by collection name."""
        pass
    
    @abstractmethod
    def get_by_action(self, action: str, skip: int = 0, limit: int = 100) -> List[T]:
        """Get audit logs by action."""
        pass
