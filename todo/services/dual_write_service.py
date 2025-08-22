import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from todo.models.postgres import (
    PostgresUser, PostgresTask, PostgresTaskLabel, PostgresDeferredDetails,
    PostgresTeam, PostgresUserTeamDetails, PostgresLabel, PostgresRole,
    PostgresTaskAssignment, PostgresWatchlist, PostgresWatchlistTask,
    PostgresUserRole, PostgresAuditLog
)

logger = logging.getLogger(__name__)


class DualWriteService:
    """
    Service for dual-write operations to MongoDB and Postgres.
    Ensures data consistency across both databases.
    """
    
    # Mapping of MongoDB collection names to Postgres models
    COLLECTION_MODEL_MAP = {
        'users': PostgresUser,
        'tasks': PostgresTask,
        'teams': PostgresTeam,
        'labels': PostgresLabel,
        'roles': PostgresRole,
        'task_assignments': PostgresTaskAssignment,
        'watchlists': PostgresWatchlist,
        'user_team_details': PostgresUserTeamDetails,
        'user_roles': PostgresUserRole,
        'audit_logs': PostgresAuditLog,
    }
    
    def __init__(self):
        self.sync_failures = []
    
    def create_document(self, collection_name: str, data: Dict[str, Any], mongo_id: str) -> bool:
        """
        Create a document in both MongoDB and Postgres.
        
        Args:
            collection_name: Name of the MongoDB collection
            data: Document data
            mongo_id: MongoDB ObjectId as string
            
        Returns:
            bool: True if both writes succeeded, False otherwise
        """
        try:
            # First, write to MongoDB (this should already be done by the calling code)
            # Then, write to Postgres
            postgres_model = self._get_postgres_model(collection_name)
            if not postgres_model:
                logger.error(f"No Postgres model found for collection: {collection_name}")
                return False
            
            # Transform data for Postgres
            postgres_data = self._transform_data_for_postgres(collection_name, data, mongo_id)
            
            # Write to Postgres
            with transaction.atomic():
                postgres_instance = postgres_model.objects.create(**postgres_data)
                logger.info(f"Successfully synced {collection_name}:{mongo_id} to Postgres")
                return True
                
        except Exception as e:
            error_msg = f"Failed to sync {collection_name}:{mongo_id} to Postgres: {str(e)}"
            logger.error(error_msg)
            self._record_sync_failure(collection_name, mongo_id, error_msg)
            return False
    
    def update_document(self, collection_name: str, mongo_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a document in both MongoDB and Postgres.
        
        Args:
            collection_name: Name of the MongoDB collection
            mongo_id: MongoDB ObjectId as string
            data: Updated document data
            
        Returns:
            bool: True if both updates succeeded, False otherwise
        """
        try:
            postgres_model = self._get_postgres_model(collection_name)
            if not postgres_model:
                logger.error(f"No Postgres model found for collection: {collection_name}")
                return False
            
            # Transform data for Postgres
            postgres_data = self._transform_data_for_postgres(collection_name, data, mongo_id)
            
            # Update in Postgres
            with transaction.atomic():
                postgres_instance = postgres_model.objects.get(mongo_id=mongo_id)
                for field, value in postgres_data.items():
                    if hasattr(postgres_instance, field):
                        setattr(postgres_instance, field, value)
                postgres_instance.sync_status = 'SYNCED'
                postgres_instance.sync_error = None
                postgres_instance.save()
                
                logger.info(f"Successfully updated {collection_name}:{mongo_id} in Postgres")
                return True
                
        except postgres_model.DoesNotExist:
            # Document doesn't exist in Postgres, create it
            return self.create_document(collection_name, data, mongo_id)
        except Exception as e:
            error_msg = f"Failed to update {collection_name}:{mongo_id} in Postgres: {str(e)}"
            logger.error(error_msg)
            self._record_sync_failure(collection_name, mongo_id, error_msg)
            return False
    
    def delete_document(self, collection_name: str, mongo_id: str) -> bool:
        """
        Delete a document from both MongoDB and Postgres.
        
        Args:
            collection_name: Name of the MongoDB collection
            mongo_id: MongoDB ObjectId as string
            
        Returns:
            bool: True if both deletes succeeded, False otherwise
        """
        try:
            postgres_model = self._get_postgres_model(collection_name)
            if not postgres_model:
                logger.error(f"No Postgres model found for collection: {collection_name}")
                return False
            
            # Soft delete in Postgres (mark as deleted)
            with transaction.atomic():
                postgres_instance = postgres_model.objects.get(mongo_id=mongo_id)
                if hasattr(postgres_instance, 'is_deleted'):
                    postgres_instance.is_deleted = True
                    postgres_instance.sync_status = 'SYNCED'
                    postgres_instance.sync_error = None
                    postgres_instance.save()
                else:
                    # If no soft delete field, actually delete the record
                    postgres_instance.delete()
                
                logger.info(f"Successfully deleted {collection_name}:{mongo_id} from Postgres")
                return True
                
        except postgres_model.DoesNotExist:
            logger.warning(f"Document {collection_name}:{mongo_id} not found in Postgres for deletion")
            return True  # Consider this a success since the goal is achieved
        except Exception as e:
            error_msg = f"Failed to delete {collection_name}:{mongo_id} from Postgres: {str(e)}"
            logger.error(error_msg)
            self._record_sync_failure(collection_name, mongo_id, error_msg)
            return False
    
    def _get_postgres_model(self, collection_name: str):
        """Get the corresponding Postgres model for a MongoDB collection."""
        return self.COLLECTION_MODEL_MAP.get(collection_name)
    
    def _transform_data_for_postgres(self, collection_name: str, data: Dict[str, Any], mongo_id: str) -> Dict[str, Any]:
        """
        Transform MongoDB document data to Postgres model format.
        
        Args:
            collection_name: Name of the MongoDB collection
            data: MongoDB document data
            mongo_id: MongoDB ObjectId as string
            
        Returns:
            Dict: Transformed data for Postgres
        """
        # Start with basic sync metadata
        postgres_data = {
            'mongo_id': mongo_id,
            'sync_status': 'SYNCED',
            'sync_error': None,
        }
        
        # Handle special cases for different collections
        if collection_name == 'tasks':
            postgres_data.update(self._transform_task_data(data))
        elif collection_name == 'teams':
            postgres_data.update(self._transform_team_data(data))
        elif collection_name == 'users':
            postgres_data.update(self._transform_user_data(data))
        elif collection_name == 'labels':
            postgres_data.update(self._transform_label_data(data))
        elif collection_name == 'roles':
            postgres_data.update(self._transform_role_data(data))
        elif collection_name == 'task_assignments':
            postgres_data.update(self._transform_task_assignment_data(data))
        elif collection_name == 'watchlists':
            postgres_data.update(self._transform_watchlist_data(data))
        elif collection_name == 'user_team_details':
            postgres_data.update(self._transform_user_team_details_data(data))
        elif collection_name == 'user_roles':
            postgres_data.update(self._transform_user_role_data(data))
        elif collection_name == 'audit_logs':
            postgres_data.update(self._transform_audit_log_data(data))
        else:
            # Generic transformation for unknown collections
            postgres_data.update(self._transform_generic_data(data))
        
        return postgres_data
    
    def _transform_task_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform task data for Postgres."""
        return {
            'display_id': data.get('displayId'),
            'title': data.get('title'),
            'description': data.get('description'),
            'priority': data.get('priority', 'LOW'),
            'status': data.get('status', 'TODO'),
            'is_acknowledged': data.get('isAcknowledged', False),
            'is_deleted': data.get('isDeleted', False),
            'started_at': data.get('startedAt'),
            'due_at': data.get('dueAt'),
            'created_at': data.get('createdAt'),
            'updated_at': data.get('updatedAt'),
            'created_by': str(data.get('createdBy', '')),
            'updated_by': str(data.get('updatedBy', '')) if data.get('updatedBy') else None,
        }
    
    def _transform_team_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform team data for Postgres."""
        return {
            'name': data.get('name'),
            'description': data.get('description'),
            'invite_code': data.get('invite_code'),
            'poc_id': str(data.get('poc_id', '')) if data.get('poc_id') else None,
            'created_by': str(data.get('created_by', '')),
            'updated_by': str(data.get('updated_by', '')),
            'is_deleted': data.get('is_deleted', False),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user data for Postgres."""
        return {
            'google_id': data.get('google_id'),
            'email_id': data.get('email_id'),
            'name': data.get('name'),
            'picture': data.get('picture'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_label_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform label data for Postgres."""
        return {
            'name': data.get('name'),
            'color': data.get('color', '#000000'),
            'description': data.get('description'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_role_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform role data for Postgres."""
        return {
            'name': data.get('name'),
            'description': data.get('description'),
            'permissions': data.get('permissions', {}),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_task_assignment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform task assignment data for Postgres."""
        return {
            'task_mongo_id': str(data.get('task_id', '')),
            'user_mongo_id': str(data.get('user_id', '')),
            'team_mongo_id': str(data.get('team_id', '')) if data.get('team_id') else None,
            'status': data.get('status', 'ASSIGNED'),
            'assigned_at': data.get('assigned_at'),
            'started_at': data.get('started_at'),
            'completed_at': data.get('completed_at'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
            'assigned_by': str(data.get('assigned_by', '')),
            'updated_by': str(data.get('updated_by', '')) if data.get('updated_by') else None,
        }
    
    def _transform_watchlist_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform watchlist data for Postgres."""
        return {
            'name': data.get('name'),
            'description': data.get('description'),
            'user_mongo_id': str(data.get('user_id', '')),
            'created_by': str(data.get('created_by', '')),
            'updated_by': str(data.get('updated_by', '')) if data.get('updated_by') else None,
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_user_team_details_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user team details data for Postgres."""
        return {
            'user_id': str(data.get('user_id', '')),
            'team_id': str(data.get('team_id', '')),
            'is_active': data.get('is_active', True),
            'created_by': str(data.get('created_by', '')),
            'updated_by': str(data.get('updated_by', '')),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_user_role_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user role data for Postgres."""
        return {
            'user_mongo_id': str(data.get('user_id', '')),
            'role_mongo_id': str(data.get('role_id', '')),
            'team_mongo_id': str(data.get('team_id', '')) if data.get('team_id') else None,
            'created_by': str(data.get('created_by', '')),
            'updated_by': str(data.get('updated_by', '')) if data.get('updated_by') else None,
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
        }
    
    def _transform_audit_log_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform audit log data for Postgres."""
        return {
            'action': data.get('action'),
            'collection_name': data.get('collection_name'),
            'document_id': str(data.get('document_id', '')),
            'user_mongo_id': str(data.get('user_id', '')) if data.get('user_id') else None,
            'old_values': data.get('old_values'),
            'new_values': data.get('new_values'),
            'ip_address': data.get('ip_address'),
            'user_agent': data.get('user_agent'),
            'timestamp': data.get('timestamp'),
        }
    
    def _transform_generic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic transformation for unknown collections."""
        # Convert MongoDB field names to snake_case and handle basic types
        transformed = {}
        for key, value in data.items():
            if key == '_id':
                continue  # Skip MongoDB _id field
            
            # Convert camelCase to snake_case
            snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
            
            # Handle ObjectId conversion
            if hasattr(value, '__str__') and len(str(value)) == 24:
                transformed[snake_key] = str(value)
            else:
                transformed[snake_key] = value
        
        return transformed
    
    def _record_sync_failure(self, collection_name: str, mongo_id: str, error: str):
        """Record a sync failure for alerting purposes."""
        failure_record = {
            'collection': collection_name,
            'mongo_id': mongo_id,
            'error': error,
            'timestamp': timezone.now(),
        }
        self.sync_failures.append(failure_record)
        
        # Log the failure
        logger.error(f"Sync failure recorded: {failure_record}")
        
        # TODO: Implement alerting mechanism (email, Slack, etc.)
        self._send_alert(failure_record)
    
    def _send_alert(self, failure_record: Dict[str, Any]):
        """Send alert for sync failure."""
        # TODO: Implement actual alerting (email, Slack, etc.)
        logger.critical(f"ALERT: Sync failure detected - {failure_record}")
        
        # For now, just log. In production, this would send emails/Slack messages
        pass
    
    def get_sync_failures(self) -> list:
        """Get list of recent sync failures."""
        return self.sync_failures.copy()
    
    def clear_sync_failures(self):
        """Clear the sync failures list."""
        self.sync_failures.clear()
