from datetime import datetime, timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Max

from todo.models import Task, TaskPriority, TaskStatus
from todo.constants.messages import ApiErrors, RepositoryErrors
from todo.constants.task import SORT_FIELD_PRIORITY, SORT_FIELD_ASSIGNEE, SORT_ORDER_DESC
from todo.exceptions.task_exceptions import TaskNotFoundException


class TaskRepository:
    @classmethod
    def list(cls, page: int, limit: int, sort_by: str, order: str, user_id: str = None) -> List[Task]:
        try:
            # Build query filter for user-specific tasks
            if user_id:
                assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
                query_filter = Q(created_by=user_id) | Q(id__in=assigned_task_ids)
            else:
                query_filter = Q()

            # Apply sorting
            if sort_by == SORT_FIELD_PRIORITY:
                sort_field = 'priority' if order == SORT_ORDER_DESC else '-priority'
            elif sort_by == SORT_FIELD_ASSIGNEE:
                # Assignee sorting is no longer supported since assignee is in separate collection
                sort_field = '-created_at' if order == SORT_ORDER_DESC else 'created_at'
            else:
                sort_field = f'-{sort_by}' if order == SORT_ORDER_DESC else sort_by

            # Calculate offset and get tasks
            offset = (page - 1) * limit
            tasks = Task.objects.filter(query_filter).order_by(sort_field)[offset:offset + limit]
            
            return list(tasks)
            
        except Exception as e:
            raise Exception(f"Error listing tasks: {str(e)}")

    @classmethod
    def _get_assigned_task_ids_for_user(cls, user_id: str) -> List[str]:
        """Get task IDs where user is assigned (either directly or as team member)."""
        try:
            # Import here to avoid circular imports
            from todo.repositories.postgres_assignee_task_details_repository import AssigneeTaskDetailsRepository
            from todo.repositories.postgres_team_repository import UserTeamDetailsRepository
            
            # Get direct assignments
            direct_assignments = AssigneeTaskDetailsRepository.get_by_assignee_id(user_id, "user")
            direct_task_ids = [str(assignment.task_id) for assignment in direct_assignments]

            # Get teams where user is a member
            user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)
            team_ids = [str(team.team_id) for team in user_teams]

            # Get tasks assigned to those teams
            team_task_ids = []
            for team_id in team_ids:
                team_assignments = AssigneeTaskDetailsRepository.get_by_assignee_id(team_id, "team")
                team_task_ids.extend([str(assignment.task_id) for assignment in team_assignments])

            return direct_task_ids + team_task_ids
            
        except Exception as e:
            raise Exception(f"Error getting assigned task IDs: {str(e)}")

    @classmethod
    def count(cls, user_id: str = None) -> int:
        try:
            if user_id:
                assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
                query_filter = Q(created_by=user_id) | Q(id__in=assigned_task_ids)
            else:
                query_filter = Q()
            
            return Task.objects.filter(query_filter).count()
            
        except Exception as e:
            raise Exception(f"Error counting tasks: {str(e)}")

    @classmethod
    def get_all(cls) -> List[Task]:
        """
        Get all tasks from the repository

        Returns:
            List[Task]: List of all task models
        """
        try:
            return list(Task.objects.all())
        except Exception as e:
            raise Exception(f"Error getting all tasks: {str(e)}")

    @classmethod
    def create(cls, task_data: dict) -> Task:
        """
        Creates a new task in the repository with a unique displayId.

        Args:
            task_data (dict): Task data to create

        Returns:
            Task: Created task with displayId
        """
        try:
            with transaction.atomic():
                # Generate display ID (simplified counter logic)
                # In a real implementation, you might want to use a separate counter table
                max_display_id = Task.objects.aggregate(
                    Max('display_id')
                )['display_id__max'] or 0
                
                next_display_id = max_display_id + 1 if isinstance(max_display_id, int) else 1
                
                # Create task
                task = Task.objects.create(
                    display_id=str(next_display_id),
                    title=task_data['title'],
                    description=task_data.get('description'),
                    priority=task_data.get('priority', TaskPriority.LOW),
                    status=task_data.get('status', TaskStatus.TODO),
                    is_acknowledged=task_data.get('is_acknowledged', False),
                    labels=task_data.get('labels', []),
                    is_deleted=task_data.get('is_deleted', False),
                    deferred_at=task_data.get('deferred_at'),
                    deferred_till=task_data.get('deferred_till'),
                    deferred_by=task_data.get('deferred_by'),
                    started_at=task_data.get('started_at'),
                    due_at=task_data.get('due_at'),
                    created_by=task_data['created_by'],
                    updated_by=task_data.get('updated_by'),
                )
                
                return task
                
        except Exception as e:
            raise Exception(f"Error creating task: {str(e)}")

    @classmethod
    def get_by_id(cls, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID

        Args:
            task_id (str): Task ID

        Returns:
            Optional[Task]: Task if found, None otherwise
        """
        try:
            return Task.objects.get(id=task_id)
        except (ObjectDoesNotExist, ValueError):
            return None

    @classmethod
    def update(cls, task_id: str, update_data: dict) -> Optional[Task]:
        """
        Update a task

        Args:
            task_id (str): Task ID
            update_data (dict): Data to update

        Returns:
            Optional[Task]: Updated task if found, None otherwise
        """
        try:
            with transaction.atomic():
                task = cls.get_by_id(task_id)
                if not task:
                    return None
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(task, field):
                        setattr(task, field, value)
                
                task.updated_at = datetime.now(timezone.utc)
                task.save()
                
                return task
                
        except Exception as e:
            raise Exception(f"Error updating task: {str(e)}")

    @classmethod
    def delete(cls, task_id: str) -> bool:
        """
        Delete a task (soft delete)

        Args:
            task_id (str): Task ID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            task = cls.get_by_id(task_id)
            if not task:
                return False
            
            task.is_deleted = True
            task.save()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting task: {str(e)}")

    @classmethod
    def get_by_display_id(cls, display_id: str) -> Optional[Task]:
        """
        Get a task by its display ID

        Args:
            display_id (str): Task display ID

        Returns:
            Optional[Task]: Task if found, None otherwise
        """
        try:
            return Task.objects.get(display_id=display_id)
        except (ObjectDoesNotExist, ValueError):
            return None
