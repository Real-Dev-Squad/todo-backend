from datetime import datetime, timezone
from typing import Optional, List
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from todo.models import User
from todo.constants.messages import RepositoryErrors
from todo.exceptions.auth_exceptions import UserNotFoundException, APIException


class UserRepository:
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except (ObjectDoesNotExist, ValueError):
            return None

    @classmethod
    def get_by_google_id(cls, google_id: str) -> Optional[User]:
        try:
            return User.objects.get(google_id=google_id)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def create_or_update(cls, user_data: dict) -> User:
        try:
            with transaction.atomic():
                google_id = user_data["google_id"]
                
                # Try to get existing user
                user = cls.get_by_google_id(google_id)
                
                if user:
                    # Update existing user
                    user.email_id = user_data["email"]
                    user.name = user_data["name"]
                    user.picture = user_data.get("picture")
                    user.updated_at = datetime.now(timezone.utc)
                    user.save()
                else:
                    # Create new user
                    user = User.objects.create(
                        google_id=google_id,
                        email_id=user_data["email"],
                        name=user_data["name"],
                        picture=user_data.get("picture"),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                
                return user

        except Exception as e:
            if isinstance(e, APIException):
                raise
            raise APIException(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(str(e)))

    @classmethod
    def search_users(cls, query: str, page: int = 1, limit: int = 10) -> tuple[List[User], int]:
        """
        Search users by name or email using case-insensitive search
        """
        try:
            # Create filter for case-insensitive search
            search_filter = Q(name__icontains=query) | Q(email_id__icontains=query)
            
            # Get total count
            total_count = User.objects.filter(search_filter).count()
            
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get paginated results
            users = User.objects.filter(search_filter).order_by('name')[offset:offset + limit]
            
            return list(users), total_count
            
        except Exception as e:
            raise APIException(f"Error searching users: {str(e)}")

    @classmethod
    def get_all_users(cls, page: int = 1, limit: int = 10) -> tuple[List[User], int]:
        """
        Get all users with pagination
        """
        try:
            total_count = User.objects.count()
            offset = (page - 1) * limit
            users = User.objects.all().order_by('name')[offset:offset + limit]
            return list(users), total_count
        except Exception as e:
            raise APIException(f"Error getting users: {str(e)}")

    @classmethod
    def delete_user(cls, user_id: str) -> bool:
        """
        Delete a user by ID
        """
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return True
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            raise APIException(f"Error deleting user: {str(e)}")
