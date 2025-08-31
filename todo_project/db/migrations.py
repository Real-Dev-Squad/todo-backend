import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from todo_project.db.config import DatabaseManager
from todo.models.label import LabelModel
from todo.models.role import RoleModel
from todo.constants.role import RoleName, RoleScope

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
            f"Fixed labels migration completed - {created_count} created, {skipped_count} skipped, {total_labels} total"
        )

        return True

    except Exception as e:
        logger.error(f"Fixed labels migration failed: {str(e)}")
        return False


def migrate_predefined_roles() -> bool:
    """Migration to add predefined roles to the system."""
    logger.info("Starting predefined roles migration")

    predefined_roles = [
        {
            "name": RoleName.MODERATOR.value,
            "scope": RoleScope.GLOBAL.value,
            "description": "Global system moderator",
            "is_active": True,
        },
        {
            "name": RoleName.OWNER.value,
            "scope": RoleScope.TEAM.value,
            "description": "Team owner with full privileges",
            "is_active": True,
        },
        {
            "name": RoleName.ADMIN.value,
            "scope": RoleScope.TEAM.value,
            "description": "Team administrator",
            "is_active": True,
        },
        {"name": RoleName.MEMBER.value, "scope": RoleScope.TEAM.value, "description": "Team member", "is_active": True},
    ]

    try:
        db_manager = DatabaseManager()
        roles_collection = db_manager.get_collection("roles")

        current_time = datetime.now(timezone.utc)
        created_count = 0
        skipped_count = 0

        for role_data in predefined_roles:
            existing = roles_collection.find_one(
                {"name": {"$regex": f"^{role_data['name']}$", "$options": "i"}, "scope": role_data["scope"]}
            )

            if existing:
                logger.info(f"Role '{role_data['name']}' ({role_data['scope']}) already exists, skipping")
                skipped_count += 1
                continue

            try:
                role_doc = {
                    "name": role_data["name"],
                    "scope": role_data["scope"],
                    "description": role_data["description"],
                    "is_active": role_data["is_active"],
                    "created_at": current_time,
                    "created_by": "system",
                }

                validated_role = RoleModel(**role_doc)
                validated_doc = validated_role.model_dump(mode="json", by_alias=True, exclude_none=True)

                result = roles_collection.insert_one(validated_doc)
                if result.inserted_id:
                    logger.info(f"Created role: {role_data['name']} ({role_data['scope']})")
                    created_count += 1

            except Exception as validation_error:
                logger.error(f"Validation failed for role '{role_data['name']}': {validation_error}")
                continue

        logger.info(f"Roles migration completed - {created_count} created, {skipped_count} skipped")
        return True

    except Exception as e:
        logger.error(f"Roles migration failed: {str(e)}")
        return False


def run_all_migrations() -> bool:
    """
    Run all database migrations.

    Returns:
        bool: True if all migrations completed successfully, False otherwise
    """
    logger.info("Starting database migrations")

    migrations = [
        ("Fixed Labels Migration", migrate_fixed_labels),
        ("Predefined Roles Migration", migrate_predefined_roles),
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
