import logging
import time
from todo_project.db.config import DatabaseManager
from todo_project.db.migrations import run_all_migrations
from todo.services.postgres_sync_service import PostgresSyncService

logger = logging.getLogger(__name__)


def initialize_database(max_retries=5, retry_delay=2):
    """
    Initialize database collections and required documents.
    Includes retry logic for Docker environments.
    """
    db_manager = DatabaseManager()

    for attempt in range(max_retries):
        try:
            if not db_manager.check_database_health():
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Database health check failed, attempt {attempt + 1}. Retrying in {retry_delay} seconds..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error("All database connection attempts failed")
                    return False
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error checking database health: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
                return False

    # Initialize counters collection
    try:
        counters_collection = db_manager.get_collection("counters")

        task_counter = counters_collection.find_one({"_id": "taskDisplayId"})
        if not task_counter:
            logger.info("Initializing taskDisplayId counter")
            counters_collection.insert_one({"_id": "taskDisplayId", "seq": 0})
        else:
            logger.info(f"taskDisplayId counter already exists with value {task_counter['seq']}")

        # Run database migrations
        migrations_success = run_all_migrations()
        if not migrations_success:
            logger.warning("Some database migrations failed, but continuing with initialization")

        try:
            postgres_sync_service = PostgresSyncService()
            postgres_sync_success = postgres_sync_service.sync_all_tables()
            if not postgres_sync_success:
                logger.warning("Some PostgreSQL table synchronizations failed, but continuing with initialization")
            else:
                logger.info("PostgreSQL table synchronization completed successfully")
        except Exception as e:
            logger.warning(f"PostgreSQL table synchronization failed: {str(e)}, but continuing with initialization")

        logger.info("Database initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False
