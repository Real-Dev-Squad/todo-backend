import logging
from django.db import connection
from django.conf import settings

from todo_project.db.config import DatabaseManager
from todo.services.dual_write_service import DualWriteService

logger = logging.getLogger(__name__)


class PostgresSyncService:
    """
    Service to synchronize PostgreSQL tables with MongoDB data.
    Checks if tables exist and copies data from MongoDB if needed.
    Currently handles labels and roles tables only.
    """

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.dual_write_service = DualWriteService()
        self.enabled = getattr(settings, "POSTGRES_SYNC_ENABLED", True)

    def sync_all_tables(self) -> bool:
        """
        Synchronize labels and roles PostgreSQL tables with MongoDB data.

        Returns:
            bool: True if all syncs completed successfully, False otherwise
        """
        if not self.enabled:
            logger.info("PostgreSQL sync is disabled, skipping")
            return True
        try:
            from django.db import connection

            connection.ensure_connection()
        except Exception as e:
            logger.warning(f"PostgreSQL not available, skipping sync: {str(e)}")
            return True

        logger.info("Starting PostgreSQL table synchronization for labels and roles")
        logger.info(f"PostgreSQL sync enabled: {self.enabled}")

        sync_operations = [
            ("labels", self._sync_labels_table),
            ("roles", self._sync_roles_table),
        ]

        success_count = 0
        total_operations = len(sync_operations)

        for table_name, sync_func in sync_operations:
            try:
                logger.info(f"Syncing table: {table_name}")
                if sync_func():
                    logger.info(f"Successfully synced table: {table_name}")
                    success_count += 1
                else:
                    logger.error(f"Failed to sync table: {table_name}")
            except Exception as e:
                logger.error(f"Error syncing table {table_name}: {str(e)}")

        logger.info(f"PostgreSQL sync completed - {success_count}/{total_operations} tables synced successfully")
        return success_count == total_operations

    def _check_table_exists(self, table_name: str) -> bool:
        """
        Check if a PostgreSQL table exists.

        Args:
            table_name: Name of the table to check

        Returns:
            bool: True if table exists, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """,
                    [table_name],
                )
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {str(e)}")
            return False

    def _get_mongo_collection_count(self, collection_name: str) -> int:
        """
        Get the count of documents in a MongoDB collection.

        Args:
            collection_name: Name of the MongoDB collection

        Returns:
            int: Number of documents in the collection
        """
        try:
            collection = self.db_manager.get_collection(collection_name)

            # Labels use isDeleted field for soft deletes
            if collection_name == "labels":
                return collection.count_documents({"isDeleted": {"$ne": True}})
            else:
                # For roles and other collections without soft delete, count all documents
                return collection.count_documents({})

        except Exception as e:
            logger.error(f"Error getting count for collection {collection_name}: {str(e)}")
            return 0

    def _get_postgres_table_count(self, table_name: str) -> int:
        """
        Get the count of records in a PostgreSQL table.

        Args:
            table_name: Name of the PostgreSQL table

        Returns:
            int: Number of records in the table
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting count for table {table_name}: {str(e)}")
            return 0

    def _sync_labels_table(self) -> bool:
        """Synchronize the labels table."""
        table_name = "postgres_labels"

        if not self._check_table_exists(table_name):
            logger.warning(f"Table {table_name} does not exist, skipping sync")
            return True

        mongo_count = self._get_mongo_collection_count("labels")
        postgres_count = self._get_postgres_table_count(table_name)

        if postgres_count >= mongo_count:
            logger.info(f"Labels table already has {postgres_count} records, MongoDB has {mongo_count}. Skipping sync.")
            return True

        logger.info(f"Syncing labels: MongoDB has {mongo_count} records, PostgreSQL has {postgres_count} records")
        logger.info(f"Will sync {mongo_count - postgres_count} labels to PostgreSQL")

        try:
            collection = self.db_manager.get_collection("labels")
            labels = collection.find({"isDeleted": {"$ne": True}})

            synced_count = 0
            for label in labels:
                try:
                    # Check if label already exists in PostgreSQL
                    try:
                        from todo.models.postgres.label import PostgresLabel
                    except Exception:
                        logger.warning("PostgreSQL models not available, skipping sync")
                        return False

                    existing = PostgresLabel.objects.filter(mongo_id=str(label["_id"])).first()
                    if existing:
                        continue

                    # Transform data for PostgreSQL
                    postgres_data = self.dual_write_service._transform_label_data(label)
                    postgres_data["mongo_id"] = str(label["_id"])
                    postgres_data["sync_status"] = "SYNCED"

                    logger.debug(f"Creating label in PostgreSQL: {postgres_data}")

                    # Create in PostgreSQL
                    PostgresLabel.objects.create(**postgres_data)
                    synced_count += 1

                except Exception as e:
                    logger.error(f"Error syncing label {label.get('_id')}: {str(e)}")
                    continue

            logger.info(f"Successfully synced {synced_count} labels to PostgreSQL")
            return True

        except Exception as e:
            logger.error(f"Error syncing labels table: {str(e)}")
            return False

    def _sync_roles_table(self) -> bool:
        """Synchronize the roles table."""
        table_name = "postgres_roles"

        if not self._check_table_exists(table_name):
            logger.warning(f"Table {table_name} does not exist, skipping sync")
            return True

        mongo_count = self._get_mongo_collection_count("roles")
        postgres_count = self._get_postgres_table_count(table_name)

        if postgres_count >= mongo_count:
            logger.info(f"Roles table already has {postgres_count} records, MongoDB has {mongo_count}. Skipping sync.")
            return True

        logger.info(f"Syncing roles: MongoDB has {mongo_count} records, PostgreSQL has {postgres_count} records")

        try:
            collection = self.db_manager.get_collection("roles")
            roles = collection.find({})

            synced_count = 0
            for role in roles:
                try:
                    try:
                        from todo.models.postgres.role import PostgresRole
                    except Exception:
                        logger.warning("PostgreSQL models not available, skipping sync")
                        return False

                    existing = PostgresRole.objects.filter(mongo_id=str(role["_id"])).first()
                    if existing:
                        continue

                    postgres_data = self.dual_write_service._transform_role_data(role)
                    postgres_data["mongo_id"] = str(role["_id"])
                    postgres_data["sync_status"] = "SYNCED"

                    PostgresRole.objects.create(**postgres_data)
                    synced_count += 1

                except Exception as e:
                    logger.error(f"Error syncing role {role.get('_id')}: {str(e)}")
                    continue

            logger.info(f"Successfully synced {synced_count} roles to PostgreSQL")
            return True

        except Exception as e:
            logger.error(f"Error syncing roles table: {str(e)}")
            return False
