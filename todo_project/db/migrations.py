import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
import uuid

from todo_project.db.config import DatabaseManager
from todo.models.label import LabelModel  # Mongo schema
from todo.models.postgres.label import Label as PostgresLabel  # Django ORM
from todo.models.postgres.user import User  # <-- Import your User model

logger = logging.getLogger(__name__)


def get_or_create_system_user() -> User:
    """
    Get or create a system user for `created_by`.
    """
    system_email = "system@internal.local"

    system_user = User.objects.filter(email_id=system_email).first()
    if not system_user:
        system_user = User.objects.create(
            google_id="system-internal",
            email_id=system_email,
            name="System User",
        )
        logger.info(f"Created system user: {system_user.id}")
    return system_user


def migrate_fixed_labels_parallel() -> bool:
    """
    Add fixed labels to MongoDB + Postgres in parallel, ensuring same UUID and system user.
    """
    logger.info("Starting fixed labels parallel migration")

    fixed_labels: List[Dict[str, Any]] = [
        {"name": "Feature", "color": "#22c55e", "description": "New feature implementation"},
        {"name": "Bug", "color": "#ef4444", "description": "Bug fixes and error corrections"},
        {"name": "Refactoring/Optimization", "color": "#f59e0b", "description": "Refactoring and optimization"},
        {"name": "API", "color": "#3b82f6", "description": "API development and integration"},
        {"name": "UI/UX", "color": "#8b5cf6", "description": "User interface and user experience improvements"},
        {"name": "Testing", "color": "#06b6d4", "description": "Testing and quality assurance"},
        {"name": "Documentation", "color": "#64748b", "description": "Documentation and guides"},
        {"name": "Review", "color": "#ec4899", "description": "Code review and peer review tasks"},
    ]

    db_manager = DatabaseManager()
    labels_collection = db_manager.get_collection("labels")
    now = datetime.now(timezone.utc)

    # ✅ get system user once
    system_user = get_or_create_system_user()

    def upsert_label(label_data):
        # MongoDB check
        mongo_existing = labels_collection.find_one(
            {"name": {"$regex": f"^{label_data['name']}$", "$options": "i"}, "isDeleted": {"$ne": True}}
        )
        mongo_uuid = str(mongo_existing["_id"]) if mongo_existing else None

        # Postgres check
        try:
            pg_existing = PostgresLabel.objects.filter(name__iexact=label_data["name"]).first()
        except Exception as e:
            logger.error(f"[Postgres] Error checking label '{label_data['name']}': {e}")
            pg_existing = None
        pg_uuid = str(pg_existing.id) if pg_existing else None

        # Pick UUID
        label_uuid = mongo_uuid or pg_uuid or str(uuid.uuid4())

        # Mongo upsert
        label_doc = {
            "_id": label_uuid,
            "name": label_data["name"],
            "color": label_data["color"],
            "description": label_data["description"],
            "isDeleted": False,
            "createdAt": now,
            "updatedAt": None,
            "createdBy": str(system_user.id),
            "updatedBy": None,
        }
        try:
            LabelModel(**label_doc)  # validate
            labels_collection.update_one({"_id": label_uuid}, {"$set": label_doc}, upsert=True)
            logger.info(f"[MongoDB] Upserted label '{label_data['name']}' UUID: {label_uuid}")
        except Exception as e:
            logger.error(f"[MongoDB] Failed to upsert '{label_data['name']}': {e}")

        # Postgres upsert
        try:
            if pg_existing:
                updated = False
                if (
                    pg_existing.name != label_data["name"]
                    or pg_existing.color != label_data["color"]
                    or getattr(pg_existing, "description", "") != label_data["description"]
                    or pg_existing.is_deleted
                ):
                    pg_existing.name = label_data["name"]
                    pg_existing.color = label_data["color"]
                    if hasattr(pg_existing, "description"):
                        pg_existing.description = label_data["description"]
                    pg_existing.is_deleted = False
                    pg_existing.updated_by = system_user
                    pg_existing.updated_at = now
                    pg_existing.save()
                    updated = True
                if updated:
                    logger.info(f"[Postgres] Updated label '{label_data['name']}' UUID: {label_uuid}")
                else:
                    logger.info(f"[Postgres] Label '{label_data['name']}' already up-to-date.")
            else:
                fields = {f.name for f in PostgresLabel._meta.get_fields()}
                kwargs = dict(
                    id=label_uuid,
                    name=label_data["name"],
                    color=label_data["color"],
                    is_deleted=False,
                    created_at=now,
                    updated_at=None,
                    created_by=system_user,
                    updated_by=None,
                )
                if "description" in fields:
                    kwargs["description"] = label_data["description"]
                PostgresLabel.objects.create(**kwargs)
                logger.info(f"[Postgres] Created label '{label_data['name']}' UUID: {label_uuid}")
        except Exception as e:
            logger.error(f"[Postgres] Failed to upsert '{label_data['name']}': {e}")

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(upsert_label, label) for label in fixed_labels]
        wait(futures, return_when=ALL_COMPLETED)

    logger.info("Finished labels parallel migration.")
    return True


def run_all_migrations() -> bool:
    logger.info("Running all DB migrations")
    migrations = [
        ("Fixed Labels Parallel Migration", migrate_fixed_labels_parallel),
    ]
    success = 0
    for name, func in migrations:
        try:
            logger.info(f"Running: {name}")
            if func():
                success += 1
                logger.info(f"{name} ✅")
            else:
                logger.error(f"{name} ❌")
        except Exception as e:
            logger.error(f"{name} Exception: {str(e)}")
    logger.info(f"Migrations done: {success}/{len(migrations)} successful")
    return success == len(migrations)
