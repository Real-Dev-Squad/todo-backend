from todo.models.audit_log import AuditLogModel
from todo.repositories.common.mongo_repository import MongoRepository
from datetime import datetime, timezone
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService


class AuditLogRepository(MongoRepository):
    collection_name = AuditLogModel.collection_name

    @classmethod
    def create(cls, audit_log: AuditLogModel) -> AuditLogModel:
        collection = cls.get_collection()
        audit_log.timestamp = datetime.now(timezone.utc)
        audit_log_dict = audit_log.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(audit_log_dict)
        audit_log.id = insert_result.inserted_id

        dual_write_service = EnhancedDualWriteService()
        audit_log_data = {
            "task_id": str(audit_log.task_id) if audit_log.task_id else None,
            "team_id": str(audit_log.team_id) if audit_log.team_id else None,
            "previous_executor_id": str(audit_log.previous_executor_id) if audit_log.previous_executor_id else None,
            "new_executor_id": str(audit_log.new_executor_id) if audit_log.new_executor_id else None,
            "spoc_id": str(audit_log.spoc_id) if audit_log.spoc_id else None,
            "action": audit_log.action,
            "timestamp": audit_log.timestamp,
            "status_from": audit_log.status_from,
            "status_to": audit_log.status_to,
            "assignee_from": str(audit_log.assignee_from) if audit_log.assignee_from else None,
            "assignee_to": str(audit_log.assignee_to) if audit_log.assignee_to else None,
            "performed_by": str(audit_log.performed_by) if audit_log.performed_by else None,
        }

        dual_write_success = dual_write_service.create_document(
            collection_name="audit_logs", data=audit_log_data, mongo_id=str(audit_log.id)
        )

        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync audit log {audit_log.id} to Postgres")

        return audit_log

    @classmethod
    def get_by_team_id(cls, team_id: str) -> list[AuditLogModel]:
        collection = cls.get_collection()
        logs = collection.find({"team_id": team_id}).sort("timestamp", -1)
        return [AuditLogModel(**log) for log in logs]
