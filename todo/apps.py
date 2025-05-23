from django.apps import AppConfig
import logging
from todo.constants.messages import RepositoryErrors
import sys

logger = logging.getLogger(__name__)


class TodoConfig(AppConfig):
    name = "todo"

    def ready(self):
        """Initialize application components when Django starts"""

        if "test" in sys.argv:
            logger.info("Test mode detected - skipping database initialization")
            return

        from todo_project.db.init import initialize_database

        try:
            initialize_database()
        except Exception as e:
            logger.error(RepositoryErrors.DB_INIT_FAILED.format(str(e)))
