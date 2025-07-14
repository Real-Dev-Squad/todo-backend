from datetime import datetime, timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from todo.models import Label


class LabelRepository:
    @classmethod
    def get_by_id(cls, label_id: str) -> Optional[Label]:
        try:
            return Label.objects.get(id=label_id)
        except (ObjectDoesNotExist, ValueError):
            return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional[Label]:
        try:
            return Label.objects.get(name=name, is_deleted=False)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def create(cls, label_data: dict) -> Label:
        try:
            with transaction.atomic():
                label = Label.objects.create(
                    name=label_data['name'],
                    color=label_data['color'],
                    is_deleted=label_data.get('is_deleted', False),
                    created_by=label_data['created_by'],
                    updated_by=label_data.get('updated_by'),
                )
                
                return label
                
        except Exception as e:
            raise Exception(f"Error creating label: {str(e)}")

    @classmethod
    def update(cls, label_id: str, update_data: dict) -> Optional[Label]:
        try:
            with transaction.atomic():
                label = cls.get_by_id(label_id)
                if not label:
                    return None
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(label, field):
                        setattr(label, field, value)
                
                label.updated_at = datetime.now(timezone.utc)
                label.save()
                
                return label
                
        except Exception as e:
            raise Exception(f"Error updating label: {str(e)}")

    @classmethod
    def delete(cls, label_id: str) -> bool:
        try:
            label = cls.get_by_id(label_id)
            if not label:
                return False
            
            label.is_deleted = True
            label.save()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting label: {str(e)}")

    @classmethod
    def get_all_active(cls) -> List[Label]:
        try:
            return list(Label.objects.filter(is_deleted=False))
        except Exception as e:
            raise Exception(f"Error getting all active labels: {str(e)}")

    @classmethod
    def search_labels(cls, query: str, page: int = 1, limit: int = 10) -> tuple[List[Label], int]:
        """
        Search labels by name
        """
        try:
            from django.db.models import Q
            
            # Create filter for case-insensitive search
            search_filter = Q(name__icontains=query) & Q(is_deleted=False)
            
            # Get total count
            total_count = Label.objects.filter(search_filter).count()
            
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get paginated results
            labels = Label.objects.filter(search_filter).order_by('name')[offset:offset + limit]
            
            return list(labels), total_count
            
        except Exception as e:
            raise Exception(f"Error searching labels: {str(e)}")

    @classmethod
    def get_by_ids(cls, label_ids: List[str]) -> List[Label]:
        """
        Get labels by their IDs
        """
        try:
            return list(Label.objects.filter(id__in=label_ids, is_deleted=False))
        except Exception as e:
            raise Exception(f"Error getting labels by IDs: {str(e)}")
