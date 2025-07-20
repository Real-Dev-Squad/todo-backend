from todo.models.audit_log import AuditLogModel
from todo.repositories.common.mongo_repository import MongoRepository
from datetime import datetime, timezone
import uuid
from todo.models.postgres.audit_log import AuditLog as PostgresAuditLogs
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from todo.utils.retry_utils import retry
from django.db import transaction


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

    @classmethod
    def create_parallel(cls, audit_log: AuditLogModel) -> AuditLogModel:
        collection = cls.get_collection()
        new_audit_log_id = str(uuid.uuid4())
        audit_log.timestamp = datetime.now(timezone.utc)
        audit_log_dict = audit_log.model_dump(mode="json", by_alias=True, exclude_none=True)
        audit_log_dict["_id"] = new_audit_log_id

        def write_mongo():
            session = cls._get_client().start_session()
            with session.start_transaction():
                insert_result = collection.insert_one(audit_log_dict, session=session)
                return insert_result.inserted_id

        def write_postgres():
            with transaction.atomic():
                PostgresAuditLogs.objects.create(
                    id=new_audit_log_id,
                    task_id=audit_log.task_id,
                    team_id=audit_log.team_id,
                    previous_executor_id=audit_log.previous_executor_id,
                    new_executor_id=audit_log.new_executor_id,
                    spoc_id=audit_log.spoc_id,
                    action=audit_log.action,
                    timestamp=audit_log.timestamp,
                )
                return "postgres_success"

        exceptions = []
        mongo_id = None
        postgres_done = False

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if isinstance(res, str) and res == "postgres_success":
                        postgres_done = True
                    else:
                        mongo_id = res
                except Exception as exc:
                    exceptions.append(exc)
                    print(f"[ERROR] Write failed: {exc}")

        if exceptions:
            if mongo_id and not postgres_done:
                collection.delete_one({"_id": new_audit_log_id})
                print(f"[COMPENSATION] Rolled back Mongo for audit_log {new_audit_log_id}")
            if postgres_done and not mongo_id:
                with transaction.atomic():
                    PostgresAuditLogs.objects.filter(id=new_audit_log_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for audit_log {new_audit_log_id}")
            raise Exception(f"AuditLog creation failed: {exceptions}")

        audit_log.id = mongo_id
        return audit_log
