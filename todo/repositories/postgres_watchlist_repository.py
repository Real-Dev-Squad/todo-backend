from datetime import datetime, timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from todo.models import Watchlist


class WatchlistRepository:
    @classmethod
    def get_by_id(cls, watchlist_id: str) -> Optional[Watchlist]:
        try:
            return Watchlist.objects.get(id=watchlist_id)
        except (ObjectDoesNotExist, ValueError):
            return None

    @classmethod
    def get_by_task_id(cls, task_id: str) -> List[Watchlist]:
        try:
            return list(Watchlist.objects.filter(task_id=task_id, is_active=True))
        except Exception as e:
            raise Exception(f"Error getting watchlist by task ID: {str(e)}")

    @classmethod
    def get_by_user_id(cls, user_id: str) -> List[Watchlist]:
        try:
            return list(Watchlist.objects.filter(user_id=user_id, is_active=True))
        except Exception as e:
            raise Exception(f"Error getting watchlist by user ID: {str(e)}")

    @classmethod
    def get_by_user_and_task(cls, user_id: str, task_id: str) -> Optional[Watchlist]:
        try:
            return Watchlist.objects.get(
                user_id=user_id,
                task_id=task_id,
                is_active=True
            )
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error getting watchlist entry: {str(e)}")

    @classmethod
    def create(cls, watchlist_data: dict) -> Watchlist:
        try:
            with transaction.atomic():
                watchlist = Watchlist.objects.create(
                    task_id=watchlist_data['task_id'],
                    user_id=watchlist_data['user_id'],
                    is_active=watchlist_data.get('is_active', True),
                    created_by=watchlist_data['created_by'],
                    updated_by=watchlist_data.get('updated_by'),
                )
                
                return watchlist
                
        except Exception as e:
            raise Exception(f"Error creating watchlist entry: {str(e)}")

    @classmethod
    def update(cls, watchlist_id: str, update_data: dict) -> Optional[Watchlist]:
        try:
            with transaction.atomic():
                watchlist = cls.get_by_id(watchlist_id)
                if not watchlist:
                    return None
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(watchlist, field):
                        setattr(watchlist, field, value)
                
                watchlist.updated_at = datetime.now(timezone.utc)
                watchlist.save()
                
                return watchlist
                
        except Exception as e:
            raise Exception(f"Error updating watchlist entry: {str(e)}")

    @classmethod
    def delete(cls, watchlist_id: str) -> bool:
        try:
            watchlist = cls.get_by_id(watchlist_id)
            if not watchlist:
                return False
            
            watchlist.is_active = False
            watchlist.save()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting watchlist entry: {str(e)}")

    @classmethod
    def delete_by_user_and_task(cls, user_id: str, task_id: str) -> bool:
        try:
            watchlist = cls.get_by_user_and_task(user_id, task_id)
            if not watchlist:
                return False
            
            watchlist.is_active = False
            watchlist.save()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting watchlist entry: {str(e)}")

    @classmethod
    def get_all_active(cls) -> List[Watchlist]:
        try:
            return list(Watchlist.objects.filter(is_active=True))
        except Exception as e:
            raise Exception(f"Error getting all active watchlist entries: {str(e)}")

    @classmethod
    def is_user_watching_task(cls, user_id: str, task_id: str) -> bool:
        """
        Check if a user is watching a specific task
        """
        try:
            return Watchlist.objects.filter(
                user_id=user_id,
                task_id=task_id,
                is_active=True
            ).exists()
        except Exception as e:
            raise Exception(f"Error checking if user is watching task: {str(e)}")

    @classmethod
    def get_watchers_for_task(cls, task_id: str) -> List[str]:
        """
        Get all user IDs watching a specific task
        """
        try:
            watchlist_entries = Watchlist.objects.filter(
                task_id=task_id,
                is_active=True
            ).values_list('user_id', flat=True)
            
            return list(watchlist_entries)
        except Exception as e:
            raise Exception(f"Error getting watchers for task: {str(e)}")
