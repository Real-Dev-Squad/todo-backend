from django.apps import AppConfig
import logging
import sys

logger = logging.getLogger(__name__)


class TodoConfig(AppConfig):
    name = "todo"

    def ready(self):
        """Initialize application components when Django starts"""

        if "test" in sys.argv:
            logger.info("Test mode detected - skipping database initialization")
            return
