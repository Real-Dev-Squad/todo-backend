from http import HTTPStatus
from django.urls import reverse
from django.conf import settings
from bson import ObjectId

from todo.constants.messages import ValidationErrors
from todo.tests.fixtures.label import label_db_data
from todo.tests.integration.base_mongo_test import BaseMongoTestCase
from todo.constants.messages import ApiErrors
from todo.utils.jwt_utils import generate_token_pair


class AuthenticatedMongoTestCase(BaseMongoTestCase):
    def setUp(self):
        super().setUp()
        self._setup_auth_cookies()

    def _setup_auth_cookies(self):
        user_data = {
            "user_id": str(ObjectId()),
            "google_id": "test_google_id",
            "email": "test@example.com",
            "name": "Test User",
        }
        tokens = generate_token_pair(user_data)
        self.client.cookies["ext-access"] = tokens["access_token"]
        self.client.cookies["ext-refresh"] = tokens["refresh_token"]


class LabelListAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.labels.delete_many({})
        self.label_docs = []

        for label in label_db_data:
            label_doc = label.copy()
            label_doc["_id"] = label_doc.pop("id") if "id" in label_doc else ObjectId()
            self.db.labels.insert_one(label_doc)
            self.label_docs.append(label_doc)

        self.url = reverse("labels")

    def test_get_labels_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertEqual(len(data["labels"]), len(self.label_docs))
        self.assertEqual(data["total"], len(self.label_docs))

        for actual_label, expected_label in zip(data["labels"], self.label_docs):
            self.assertEqual(actual_label["name"], expected_label["name"])
            self.assertEqual(actual_label["color"], expected_label["color"])

    def test_get_labels_with_search_match(self):
        keyword = self.label_docs[0]["name"][:3]
        response = self.client.get(self.url, {"search": keyword})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertGreater(len(data["labels"]), 0)
        self.assertTrue(any(keyword.lower() in label["name"].lower() for label in data["labels"]))

    def test_get_labels_with_search_no_match(self):
        response = self.client.get(self.url, {"search": "no-match-keyword-xyz"})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertEqual(data["labels"], [])
        self.assertEqual(data["total"], 0)

    def test_get_labels_with_invalid_pagination(self):
        response = self.client.get(self.url, {"page": 99999, "limit": 10})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertEqual(data["labels"], [])
        self.assertIsNotNone(data["error"])
        self.assertEqual(data["error"]["message"], ApiErrors.PAGE_NOT_FOUND)
        self.assertEqual(data["error"]["code"], "PAGE_NOT_FOUND")

    def test_get_labels_uses_default_pagination(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertIn("page", data)
        self.assertIn("limit", data)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 10)

    def test_get_labels_invalid_limit_type_query_param(self):
        response = self.client.get(self.url, {"limit": "invalid"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["errors"][0]["source"]["parameter"], "limit")
        self.assertIn("A valid integer is required.", data["errors"][0]["detail"])

    def test_get_labels_invalid_label_query_param(self):
        response = self.client.get(self.url, {"limit": 0})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["errors"][0]["source"]["parameter"], "limit")
        self.assertIn(ValidationErrors.LIMIT_POSITIVE, data["errors"][0]["detail"])

    def test_get_labels_greater_than_max_limit_query_param(self):
        response = self.client.get(self.url, {"limit": 1000})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        MAX_PAGE_LIMIT = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]

        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["errors"][0]["source"]["parameter"], "limit")
        self.assertIn(f"Ensure this value is less than or equal to {MAX_PAGE_LIMIT}.", data["errors"][0]["detail"])

    def test_get_labels_invalid_page_type_query_param(self):
        response = self.client.get(self.url, {"page": "invalid"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["errors"][0]["source"]["parameter"], "page")
        self.assertIn("A valid integer is required.", data["errors"][0]["detail"])

    def test_get_labels_invalid_page_query_param(self):
        response = self.client.get(self.url, {"page": 0})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        data = response.json()
        self.assertEqual(data["statusCode"], 400)
        self.assertEqual(data["errors"][0]["source"]["parameter"], "page")
        self.assertIn(ValidationErrors.PAGE_POSITIVE, data["errors"][0]["detail"])
