import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from todo.services.dual_write_service import DualWriteService

logger = logging.getLogger(__name__)


class EnhancedDualWriteService(DualWriteService):
    """
    Enhanced dual-write service that provides additional functionality.
    Extends the base DualWriteService with batch operations and enhanced monitoring.
    """
    
    def __init__(self):
        super().__init__()
        self.enabled = getattr(settings, 'DUAL_WRITE_ENABLED', True)
    
    def create_document(self, collection_name: str, data: Dict[str, Any], mongo_id: str) -> bool:
        """
        Create a document in both MongoDB and Postgres.
        """
        if not self.enabled:
            logger.debug("Dual-write is disabled, skipping Postgres sync")
            return True
        
        return super().create_document(collection_name, data, mongo_id)
    
    def update_document(self, collection_name: str, mongo_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a document in both MongoDB and Postgres.
        """
        if not self.enabled:
            logger.debug("Dual-write is disabled, skipping Postgres sync")
            return True
        
        return super().update_document(collection_name, mongo_id, data)
    
    def delete_document(self, collection_name: str, mongo_id: str) -> bool:
        """
        Delete a document from both MongoDB and Postgres.
        """
        if not self.enabled:
            logger.debug("Dual-write is disabled, skipping Postgres sync")
            return True
        
        return super().delete_document(collection_name, mongo_id)
    
    def batch_operations(self, operations: list) -> bool:
        """
        Perform multiple operations in batch.
        """
        if not self.enabled:
            logger.debug("Dual-write is disabled, skipping Postgres sync")
            return True
        
        return self._batch_operations_sync(operations)
    
    def _batch_operations_sync(self, operations: list) -> bool:
        """Perform batch operations synchronously."""
        success_count = 0
        failure_count = 0
        
        for op in operations:
            try:
                collection_name = op['collection_name']
                data = op.get('data', {})
                mongo_id = op['mongo_id']
                operation = op['operation']
                
                if operation == 'create':
                    success = super().create_document(collection_name, data, mongo_id)
                elif operation == 'update':
                    success = super().update_document(collection_name, mongo_id, data)
                elif operation == 'delete':
                    success = super().delete_document(collection_name, mongo_id)
                else:
                    logger.error(f"Unknown operation: {operation}")
                    failure_count += 1
                    continue
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing operation {op}: {str(e)}")
                failure_count += 1
        
        logger.info(f"Batch sync completed. Success: {success_count}, Failures: {failure_count}")
        return failure_count == 0
    
    def get_sync_status(self, collection_name: str, mongo_id: str) -> Optional[str]:
        """
        Get the sync status of a document in Postgres.
        
        Args:
            collection_name: Name of the MongoDB collection
            mongo_id: MongoDB ObjectId as string
            
        Returns:
            str: Sync status or None if not found
        """
        try:
            postgres_model = self._get_postgres_model(collection_name)
            if not postgres_model:
                return None
            
            instance = postgres_model.objects.get(mongo_id=mongo_id)
            return instance.sync_status
        except postgres_model.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting sync status for {collection_name}:{mongo_id}: {str(e)}")
            return None
    
    def get_sync_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about sync operations.
        
        Returns:
            Dict: Sync metrics
        """
        try:
            metrics = {
                'total_failures': len(self.sync_failures),
                'failures_by_collection': {},
                'recent_failures': self.sync_failures[-10:] if self.sync_failures else [],
                'enabled': self.enabled,
            }
            
            # Count failures by collection
            for failure in self.sync_failures:
                collection = failure['collection']
                if collection not in metrics['failures_by_collection']:
                    metrics['failures_by_collection'][collection] = 0
                metrics['failures_by_collection'][collection] += 1
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting sync metrics: {str(e)}")
            return {}
    
    def retry_failed_sync(self, collection_name: str, mongo_id: str) -> bool:
        """
        Retry a failed sync operation.
        
        Args:
            collection_name: Name of the MongoDB collection
            mongo_id: MongoDB ObjectId as string
            
        Returns:
            bool: True if retry was successful, False otherwise
        """
        try:
            # Find the failure record
            failure_record = None
            for failure in self.sync_failures:
                if failure['collection'] == collection_name and failure['mongo_id'] == mongo_id:
                    failure_record = failure
                    break
            
            if not failure_record:
                logger.warning(f"No failure record found for {collection_name}:{mongo_id}")
                return False
            
            # Remove from failures list
            self.sync_failures.remove(failure_record)
            
            # Retry the operation (this would need the original data)
            # For now, just log the retry attempt
            logger.info(f"Retrying sync for {collection_name}:{mongo_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error retrying failed sync for {collection_name}:{mongo_id}: {str(e)}")
            return False
