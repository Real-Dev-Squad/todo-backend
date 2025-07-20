import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
import uuid
from todo_project.db.config import DatabaseManager
from todo.models.label import LabelModel
from todo.models.postgres.label import Label as PostgresLabel

logger = logging.getLogger(__name__)


def migrate_fixed_labels() -> bool:
    """
    Migration to add fixed labels to the system.
    This migration is idempotent and can be run multiple times safely.

    Labels to be added:
    1. Feature
    2. Bug
    3. Refactoring/Optimization
    4. API
    5. UI/UX
    6. Testing
    7. Documentation
    8. Review

    Returns:
        bool: True if migration completed successfully, False otherwise
    """
    logger.info("Starting fixed labels migration")

    fixed_labels: List[Dict[str, Any]] = [
        {
            "name": "Feature",
            "color": "#22c55e",
            "description": "New feature implementation",
        },
        {
            "name": "Bug",
            "color": "#ef4444",
            "description": "Bug fixes and error corrections",
        },
        {
            "name": "Refactoring/Optimization",
            "color": "#f59e0b",
            "description": "Code refactoring and performance optimization",
        },
        {
            "name": "API",
            "color": "#3b82f6",
            "description": "API development and integration",
        },
        {
            "name": "UI/UX",
            "color": "#8b5cf6",
            "description": "User interface and user experience improvements",
        },
        {
            "name": "Testing",
            "color": "#06b6d4",
            "description": "Testing and quality assurance",
        },
        {
            "name": "Documentation",
            "color": "#64748b",
            "description": "Documentation and guides",
        },
        {
            "name": "Review",
            "color": "#ec4899",
            "description": "Code review and peer review tasks",
        },
    ]

    try:
        db_manager = DatabaseManager()
        labels_collection = db_manager.get_collection("labels")

        current_time = datetime.now(timezone.utc)
        created_count = 0
        skipped_count = 0

        for label_data in fixed_labels:
            try:
                existing_label = labels_collection.find_one(
                    {"name": {"$regex": f"^{label_data['name']}$", "$options": "i"}, "isDeleted": {"$ne": True}}
                )

                if existing_label:
                    logger.info(f"Label '{label_data['name']}' already exists, skipping")
                    skipped_count += 1
                    continue

                label_document = {
                    "name": label_data["name"],
                    "color": label_data["color"],
                    "description": label_data["description"],
                    "isDeleted": False,
                    "createdAt": current_time,
                    "updatedAt": None,
                    "createdBy": "system",
                    "updatedBy": None,
                }

                try:
                    LabelModel(**label_document)
                except Exception as validation_error:
                    logger.error(f"Label validation failed for '{label_data['name']}': {validation_error}")
                    continue

                result = labels_collection.insert_one(label_document)

                if result.inserted_id:
                    logger.info(f"Successfully created label '{label_data['name']}' with ID: {result.inserted_id}")
                    created_count += 1
                else:
                    logger.error(f"Failed to create label '{label_data['name']}' - no ID returned")

            except Exception as e:
                logger.error(f"Error processing label '{label_data['name']}': {str(e)}")
                continue

        total_labels = len(fixed_labels)
        logger.info(
            f"Fixed labels migration completed - Total: {total_labels}, Created: {created_count}, Skipped: {skipped_count}"
        )

        return True

    except Exception as e:
        logger.error(f"Fixed labels migration failed with error: {str(e)}")
        return False


def migrate_fixed_labels_parallel() -> bool:
    """
    Migration to add fixed labels to both MongoDB and Postgres in parallel, using the same UUID for each label.
    This migration is idempotent and can be run multiple times safely.
    """
    logger.info("Starting fixed labels parallel migration (MongoDB + Postgres)")

    fixed_labels: List[Dict[str, Any]] = [
        {"name": "Feature", "color": "#22c55e", "description": "New feature implementation"},
        {"name": "Bug", "color": "#ef4444", "description": "Bug fixes and error corrections"},
        {"name": "Refactoring/Optimization", "color": "#f59e0b", "description": "Code refactoring and performance optimization"},
        {"name": "API", "color": "#3b82f6", "description": "API development and integration"},
        {"name": "UI/UX", "color": "#8b5cf6", "description": "User interface and user experience improvements"},
        {"name": "Testing", "color": "#06b6d4", "description": "Testing and quality assurance"},
        {"name": "Documentation", "color": "#64748b", "description": "Documentation and guides"},
        {"name": "Review", "color": "#ec4899", "description": "Code review and peer review tasks"},
    ]

    db_manager = DatabaseManager()
    labels_collection = db_manager.get_collection("labels")
    now = datetime.now(timezone.utc)
    system_user_id = uuid.uuid4()  # Or use a fixed UUID for 'system'

    def create_label(label_data):
        # Check if label exists in Postgres (case-insensitive)
        try:
            existing_pg_label = PostgresLabel.objects.filter(name__iexact=label_data["name"]).first()
        except Exception as e:
            logger.error(f"[Postgres] Error checking label '{label_data['name']}': {e}")
            existing_pg_label = None

        if existing_pg_label:
            label_uuid = str(existing_pg_label.id)
            logger.info(f"[Postgres] Label '{label_data['name']}' already exists, skipping creation")
        else:
            label_uuid = str(uuid.uuid4())
            try:
                obj = PostgresLabel.objects.create(
                    id=label_uuid,
                    name=label_data["name"],
                    color=label_data["color"],
                    is_deleted=False,
                    created_at=now,
                    updated_at=None,
                    created_by=system_user_id,
                    updated_by=None,
                )
                logger.info(f"[Postgres] Created label '{label_data['name']}' with UUID: {label_uuid}")
            except Exception as e:
                logger.error(f"[Postgres] Failed to create label '{label_data['name']}': {e}")
                return

        # MongoDB logic
        mongo_existing = labels_collection.find_one({"name": {"$regex": f"^{label_data['name']}$", "$options": "i"}, "isDeleted": {"$ne": True}})
        if not mongo_existing:
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
            try:
                LabelModel(**label_document)
                labels_collection.insert_one(label_document)
                logger.info(f"[MongoDB] Created label '{label_data['name']}' with UUID: {label_uuid}")
            except Exception as e:
                logger.error(f"[MongoDB] Failed to create label '{label_data['name']}': {e}")
        else:
            logger.info(f"[MongoDB] Label '{label_data['name']}' already exists, skipping")

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(create_label, label) for label in fixed_labels]
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

    migrations = [("Fixed Labels Migration", migrate_fixed_labels), ("Fixed Labels Parallel Migration", migrate_fixed_labels_parallel)]

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
