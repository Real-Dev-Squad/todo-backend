from todo.models.audit_log import AuditLogModel
from todo.repositories.common.mongo_repository import MongoRepository
from datetime import datetime, timezone


class AuditLogRepository(MongoRepository):
    collection_name = AuditLogModel.collection_name

    @classmethod
    def create(cls, audit_log: AuditLogModel) -> AuditLogModel:
        collection = cls.get_collection()
        audit_log.timestamp = datetime.now(timezone.utc)
        audit_log_dict = audit_log.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(audit_log_dict)
        audit_log.id = insert_result.inserted_id
        return audit_log
