import logging
from typing import Optional, Dict, Any
from django.conf import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)


class PostgreSQLDatabaseManager:
    """
    PostgreSQL Database Manager for handling database connections and health checks.
    This will be used alongside the existing MongoDB manager during migration.
    """

    __instance: Optional["PostgreSQLDatabaseManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwargs)
            cls.__instance._connection = None
        return cls.__instance

    def _get_connection_params(self) -> Dict[str, Any]:
        """Get PostgreSQL connection parameters from Django settings."""
        return {
            "host": settings.POSTGRES_CONFIG["HOST"],
            "port": settings.POSTGRES_CONFIG["PORT"],
            "database": settings.POSTGRES_CONFIG["DATABASE"],
            "user": settings.POSTGRES_CONFIG["USER"],
            "password": settings.POSTGRES_CONFIG["PASSWORD"],
        }

    def get_connection(self) -> psycopg2.extensions.connection:
        """Get a database connection."""
        if self._connection is None or self._connection.closed:
            try:
                params = self._get_connection_params()
                self._connection = psycopg2.connect(**params)
                self._connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                logger.info("PostgreSQL connection established successfully")
            except psycopg2.Error as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise
        return self._connection

    def get_cursor(self):
        """Get a context-managed cursor from the connection."""
        return self.get_connection().cursor()

    def check_database_health(self) -> bool:
        """Check if the PostgreSQL database is healthy."""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    logger.info("PostgreSQL database health check passed")
                    return True
                else:
                    logger.error("PostgreSQL database health check failed: unexpected result")
                    return False
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL database health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during PostgreSQL health check: {e}")
            return False

    def close_connection(self):
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("PostgreSQL connection closed")

    @classmethod
    def reset(cls):
        """Reset the singleton instance."""
        if cls.__instance is not None:
            cls.__instance.close_connection()
        cls.__instance = None

    def __del__(self):
        self.close_connection()
