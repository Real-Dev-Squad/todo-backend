import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
import uuid
from todo_project.db.config import DatabaseManager
from todo.models.label import LabelModel
from todo.models.postgres.label import Label as PostgresLabel

logger = logging.getLogger(__name__)


def migrate_fixed_labels_parallel() -> bool:
    """
    Migration to add fixed labels to both MongoDB and Postgres in parallel, using the same UUID for each label.
    This migration is idempotent and can be run multiple times safely.
    Ensures both databases have the same id and data for each label.
    """
    logger.info("Starting fixed labels parallel migration (MongoDB + Postgres)")

    fixed_labels: List[Dict[str, Any]] = [
        {"name": "Feature", "color": "#22c55e", "description": "New feature implementation"},
        {"name": "Bug", "color": "#ef4444", "description": "Bug fixes and error corrections"},
        {
            "name": "Refactoring/Optimization",
            "color": "#f59e0b",
            "description": "Code refactoring and performance optimization",
        },
        {"name": "API", "color": "#3b82f6", "description": "API development and integration"},
        {"name": "UI/UX", "color": "#8b5cf6", "description": "User interface and user experience improvements"},
        {"name": "Testing", "color": "#06b6d4", "description": "Testing and quality assurance"},
        {"name": "Documentation", "color": "#64748b", "description": "Documentation and guides"},
        {"name": "Review", "color": "#ec4899", "description": "Code review and peer review tasks"},
    ]

    db_manager = DatabaseManager()
    labels_collection = db_manager.get_collection("labels")
    now = datetime.now(timezone.utc)

    def upsert_label(label_data):
        # Check if label exists in MongoDB (case-insensitive)
        mongo_existing = labels_collection.find_one(
            {"name": {"$regex": f"^{label_data['name']}$", "$options": "i"}, "isDeleted": {"$ne": True}}
        )
        mongo_uuid = str(mongo_existing["_id"]) if mongo_existing else None

        # Check if label exists in Postgres (case-insensitive)
        try:
            existing_pg_label = PostgresLabel.objects.filter(name__iexact=label_data["name"]).first()
        except Exception as e:
            logger.error(f"[Postgres] Error checking label '{label_data['name']}': {e}")
            existing_pg_label = None
        pg_uuid = str(existing_pg_label.id) if existing_pg_label else None

        # Decide which UUID to use
        label_uuid = None
        if mongo_uuid and pg_uuid:
            if mongo_uuid != pg_uuid:
                logger.warning(
                    f"UUID mismatch for label '{label_data['name']}': MongoDB={mongo_uuid}, Postgres={pg_uuid}. Using MongoDB UUID."
                )
            label_uuid = mongo_uuid
        elif mongo_uuid:
            label_uuid = mongo_uuid
        elif pg_uuid:
            label_uuid = pg_uuid
        else:
            label_uuid = str(uuid.uuid4())

        # Prepare label document/data
        label_document = {
            "_id": label_uuid,
            "name": label_data["name"],
            "color": label_data["color"],
            "description": label_data["description"],
            "isDeleted": False,
            "createdAt": now,
            "updatedAt": None,
            "createdBy": "system",
            "updatedBy": None,
        }
        # Upsert in MongoDB
        try:
            LabelModel(**label_document)
            labels_collection.update_one({"_id": label_uuid}, {"$set": label_document}, upsert=True)
            logger.info(f"[MongoDB] Upserted label '{label_data['name']}' with UUID: {label_uuid}")
        except Exception as e:
            logger.error(f"[MongoDB] Failed to upsert label '{label_data['name']}': {e}")

        # Upsert in Postgres
        try:
            if existing_pg_label:
                # Update fields if needed
                updated = False
                if (
                    existing_pg_label.name != label_data["name"]
                    or existing_pg_label.color != label_data["color"]
                    or getattr(existing_pg_label, "description", None) != label_data["description"]
                    or existing_pg_label.is_deleted
                ):
                    existing_pg_label.name = label_data["name"]
                    existing_pg_label.color = label_data["color"]
                    if hasattr(existing_pg_label, "description"):
                        existing_pg_label.description = label_data["description"]
                    existing_pg_label.is_deleted = False
                    existing_pg_label.save()
                    updated = True
                if updated:
                    logger.info(f"[Postgres] Updated label '{label_data['name']}' with UUID: {label_uuid}")
                else:
                    logger.info(f"[Postgres] Label '{label_data['name']}' already up-to-date with UUID: {label_uuid}")
            else:
                # Only add description if it exists in the model
                fields = {f.name for f in PostgresLabel._meta.get_fields()}
                kwargs = dict(
                    id=label_uuid,
                    name=label_data["name"],
                    color=label_data["color"],
                    is_deleted=False,
                    created_at=now,
                    updated_at=None,
                    created_by=uuid.uuid4(),
                    updated_by=None,
                )
                if "description" in fields:
                    kwargs["description"] = label_data["description"]
                PostgresLabel.objects.create(**kwargs)
                logger.info(f"[Postgres] Created label '{label_data['name']}' with UUID: {label_uuid}")
        except Exception as e:
            logger.error(f"[Postgres] Failed to upsert label '{label_data['name']}': {e}")

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(upsert_label, label) for label in fixed_labels]
        wait(futures, return_when=ALL_COMPLETED)

    logger.info("Fixed labels parallel migration completed.")
    return True


def run_all_migrations() -> bool:
    """
    Run all database migrations.

    Returns:
        bool: True if all migrations completed successfully, False otherwise
    """
    logger.info("Starting database migrations")

    migrations = [
        ("Fixed Labels Parallel Migration", migrate_fixed_labels_parallel),
    ]

    success_count = 0

    for migration_name, migration_func in migrations:
        try:
            logger.info(f"Running {migration_name}")
            if migration_func():
                logger.info(f"{migration_name} completed successfully")
                success_count += 1
            else:
                logger.error(f"{migration_name} failed")
        except Exception as e:
            logger.error(f"{migration_name} failed with exception: {str(e)}")

    total_migrations = len(migrations)
    logger.info(f"Database migrations completed - {success_count}/{total_migrations} successful")

    return success_count == total_migrations


def create_label_in_both_dbs(name, color, description):
    db_manager = DatabaseManager()
    labels_collection = db_manager.get_collection("labels")
    now = datetime.now(timezone.utc)

    # Check MongoDB for existing label (case-insensitive)
    mongo_existing = labels_collection.find_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}, "isDeleted": {"$ne": True}}
    )

    # Check Postgres for existing label (case-insensitive)
    try:
        pg_existing = PostgresLabel.objects.filter(name__iexact=name).first()
    except Exception as e:
        print(f"[Postgres] Error checking label '{name}': {e}")
        pg_existing = None

    if mongo_existing or pg_existing:
        print(f"Label '{name}' already exists in one or both DBs. Skipping creation.")
        return

    label_uuid = str(uuid.uuid4())

    # MongoDB
    label_document = {
        "_id": label_uuid,
        "name": name,
        "color": color,
        "description": description,
        "isDeleted": False,
        "createdAt": now,
        "updatedAt": None,
        "createdBy": "system",
        "updatedBy": None,
    }
    LabelModel(**label_document)  # Validate
    labels_collection.insert_one(label_document)

    # Postgres
    # Only add description if it exists in the model
    fields = {f.name for f in PostgresLabel._meta.get_fields()}
    kwargs = dict(
        id=label_uuid,
        name=name,
        color=color,
        is_deleted=False,
        created_at=now,
        updated_at=None,
        created_by="system",
        updated_by=None,
    )
    if "description" in fields:
        kwargs["description"] = description
    PostgresLabel.objects.create(**kwargs)

    print(f"Created label '{name}' in both DBs with UUID: {label_uuid}")
