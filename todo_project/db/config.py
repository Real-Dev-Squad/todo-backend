import logging
from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)


class DatabaseManager:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwargs)
            cls.__instance._database_client = None
            cls.__instance._db = None
        return cls.__instance

    def _get_database_client(self):
        if self._database_client is None:
            self._database_client = MongoClient(settings.MONGODB_URI)
        return self._database_client

    def get_database(self):
        if self._db is None:
            self._db = self._get_database_client()[settings.DB_NAME]
        return self._db

    def get_collection(self, collection_name):
        database = self.get_database()
        return database[collection_name]

    def check_database_health(self):
        try:
            db_client = self._get_database_client()
            db_client.admin.command("ping")
            logger.info("Database connection established successfully")
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to establish database connection: {e}")
            return False
