from datetime import datetime, timezone
from bson import ObjectId
from django.test import TransactionTestCase, override_settings
from pymongo import MongoClient
from todo.models.user import UserModel
from todo.tests.testcontainers.shared_mongo import get_shared_mongo_container
from todo.utils.jwt_utils import generate_token_pair
from todo_project.db.config import DatabaseManager
from rest_framework.test import APIClient
from todo.tests.fixtures.user import google_auth_user_payload


class BaseMongoTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mongo_container = get_shared_mongo_container()
        cls.mongo_url = cls.mongo_container.get_connection_url()
        cls.mongo_client = MongoClient(cls.mongo_url)
        cls.db = cls.mongo_client.get_database("testdb")

        cls.override = override_settings(
            MONGODB_URI=cls.mongo_url, DB_NAME="testdb", FRONTEND_URL="http://localhost:3000"
        )
        cls.override.enable()
        DatabaseManager.reset()
        DatabaseManager().get_database()

    def setUp(self):
        for collection in self.db.list_collection_names():
            self.db[collection].delete_many({})

    @classmethod
    def tearDownClass(cls):
        cls.mongo_client.close()
        cls.override.disable()
        super().tearDownClass()


class AuthenticatedMongoTestCase(BaseMongoTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self._create_test_user()
        self._set_auth_cookies()

    def _create_test_user(self):
        self.user_id = ObjectId()
        self.user_data = {
            **google_auth_user_payload,
            "user_id": str(self.user_id),
        }

        self.db.users.insert_one(
            {
                "_id": self.user_id,
                "google_id": self.user_data["google_id"],
                "email_id": self.user_data["email"],
                "name": self.user_data["name"],
                "picture": self.user_data["picture"],
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
            }
        )

    def _set_auth_cookies(self):
        tokens = generate_token_pair(self.user_data)
        self.client.cookies["todo-access"] = tokens["access_token"]
        self.client.cookies["todo-refresh"] = tokens["refresh_token"]

    def get_user_model(self) -> UserModel:
        return UserModel(
            id=self.user_id,
            google_id=self.user_data["google_id"],
            email_id=self.user_data["email"],
            name=self.user_data["name"],
            picture=self.user_data["picture"],
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )
