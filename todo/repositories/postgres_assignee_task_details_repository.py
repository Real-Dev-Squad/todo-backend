from datetime import datetime, timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from todo.models import AssigneeTaskDetails


class AssigneeTaskDetailsRepository:
    @classmethod
    def get_by_assignee_id(cls, assignee_id: str, relation_type: str) -> List[AssigneeTaskDetails]:
        """
        Get assignee-task details by assignee ID and relation type

        Args:
            assignee_id (str): Assignee ID (user or team)
            relation_type (str): Type of relation ("user" or "team")

        Returns:
            List[AssigneeTaskDetails]: List of assignee-task details
        """
        try:
            return list(AssigneeTaskDetails.objects.filter(
                assignee_id=assignee_id,
                relation_type=relation_type,
                is_active=True
            ))
        except Exception as e:
            raise Exception(f"Error getting assignee task details: {str(e)}")

    @classmethod
    def get_by_task_id(cls, task_id: str) -> List[AssigneeTaskDetails]:
        """
        Get assignee-task details by task ID

        Args:
            task_id (str): Task ID

        Returns:
            List[AssigneeTaskDetails]: List of assignee-task details
        """
        try:
            return list(AssigneeTaskDetails.objects.filter(
                task_id=task_id,
                is_active=True
            ))
        except Exception as e:
            raise Exception(f"Error getting assignee task details by task ID: {str(e)}")

    @classmethod
    def create(cls, assignee_task_data: dict) -> AssigneeTaskDetails:
        """
        Create a new assignee-task relationship

        Args:
            assignee_task_data (dict): Assignee task data

        Returns:
            AssigneeTaskDetails: Created assignee-task details
        """
        try:
            with transaction.atomic():
                assignee_task = AssigneeTaskDetails.objects.create(
                    assignee_id=assignee_task_data['assignee_id'],
                    task_id=assignee_task_data['task_id'],
                    relation_type=assignee_task_data['relation_type'],
                    is_action_taken=assignee_task_data.get('is_action_taken', False),
                    is_active=assignee_task_data.get('is_active', True),
                    created_by=assignee_task_data['created_by'],
                    updated_by=assignee_task_data.get('updated_by'),
                )
                
                return assignee_task
                
        except Exception as e:
            raise Exception(f"Error creating assignee task details: {str(e)}")

    @classmethod
    def update(cls, assignee_task_id: str, update_data: dict) -> Optional[AssigneeTaskDetails]:
        """
        Update assignee-task details

        Args:
            assignee_task_id (str): Assignee task details ID
            update_data (dict): Data to update

        Returns:
            Optional[AssigneeTaskDetails]: Updated assignee-task details if found, None otherwise
        """
        try:
            with transaction.atomic():
                assignee_task = AssigneeTaskDetails.objects.get(id=assignee_task_id)
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(assignee_task, field):
                        setattr(assignee_task, field, value)
                
                assignee_task.updated_at = datetime.now(timezone.utc)
                assignee_task.save()
                
                return assignee_task
                
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error updating assignee task details: {str(e)}")

    @classmethod
    def delete(cls, assignee_task_id: str) -> bool:
        """
        Delete assignee-task details (soft delete)

        Args:
            assignee_task_id (str): Assignee task details ID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            assignee_task = AssigneeTaskDetails.objects.get(id=assignee_task_id)
            assignee_task.is_active = False
            assignee_task.save()
            return True
            
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            raise Exception(f"Error deleting assignee task details: {str(e)}")

    @classmethod
    def get_by_assignee_and_task(cls, assignee_id: str, task_id: str, relation_type: str) -> Optional[AssigneeTaskDetails]:
        """
        Get assignee-task details by assignee ID, task ID, and relation type

        Args:
            assignee_id (str): Assignee ID
            task_id (str): Task ID
            relation_type (str): Relation type

        Returns:
            Optional[AssigneeTaskDetails]: Assignee-task details if found, None otherwise
        """
        try:
            return AssigneeTaskDetails.objects.get(
                assignee_id=assignee_id,
                task_id=task_id,
                relation_type=relation_type,
                is_active=True
            )
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error getting assignee task details: {str(e)}")

    @classmethod
    def get_all_active(cls) -> List[AssigneeTaskDetails]:
        """
        Get all active assignee-task details

        Returns:
            List[AssigneeTaskDetails]: List of all active assignee-task details
        """
        try:
            return list(AssigneeTaskDetails.objects.filter(is_active=True))
        except Exception as e:
            raise Exception(f"Error getting all active assignee task details: {str(e)}")
