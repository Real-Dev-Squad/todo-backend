from django.test import TransactionTestCase, override_settings
from pymongo import MongoClient
from todo.tests.testcontainers.shared_mongo import get_shared_mongo_container
from todo_project.db.config import DatabaseManager

class BaseMongoTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mongo_container = get_shared_mongo_container()
        cls.mongo_url = cls.mongo_container.get_connection_url()
        cls.mongo_client = MongoClient(cls.mongo_url)
        cls.db = cls.mongo_client.get_database("testdb")

        cls.override = override_settings(
            MONGODB_URI=cls.mongo_url,
            DB_NAME="testdb",
        )
        cls.override.enable()
        DatabaseManager().reset()

    def setUp(self):
        for collection in self.db.list_collection_names():
            self.db[collection].delete_many({})

    @classmethod
    def tearDownClass(cls):
        cls.mongo_client.close()
        cls.override.disable()
        super().tearDownClass()
