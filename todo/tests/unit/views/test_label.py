from rest_framework.test import APIClient, APISimpleTestCase
from rest_framework.reverse import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from bson.objectid import ObjectId
from rest_framework.response import Response

from todo.dto.responses.get_labels_response import GetLabelsResponse
from todo.dto.label_dto import LabelDTO
from todo.constants.messages import ApiErrors
from todo.utils.jwt_utils import generate_token_pair


class AuthenticatedTestCase(APISimpleTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
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


class LabelViewTests(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("labels")
        self.label_dtos = [
            LabelDTO(id="1", name="Bug", color="red"),
            LabelDTO(id="2", name="Feature", color="blue"),
        ]

    @patch("todo.services.label_service.LabelService.get_labels")
    def test_get_labels_returns_200_for_valid_params(self, mock_get_labels: Mock):
        mock_get_labels.return_value = GetLabelsResponse(labels=[self.label_dtos[0]], total=1, page=1, limit=10)

        response: Response = self.client.get(self.url, {"page": 1, "limit": 10, "search": "bug"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_labels.assert_called_once_with(page=1, limit=10, search="bug")
        self.assertEqual(response.data["total"], 1)

    @patch("todo.services.label_service.LabelService.get_labels")
    def test_get_labels_uses_default_values(self, mock_get_labels: Mock):
        mock_get_labels.return_value = GetLabelsResponse(labels=self.label_dtos, total=2, page=1, limit=10)

        response: Response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_labels.assert_called_once_with(page=1, limit=10, search="")
        self.assertEqual(response.data["total"], 2)

    @patch("todo.services.label_service.LabelService.get_labels")
    def test_get_labels_strips_whitespace_from_search(self, mock_get_labels: Mock):
        mock_get_labels.return_value = GetLabelsResponse(labels=[self.label_dtos[0]], total=1, page=1, limit=10)

        response: Response = self.client.get(self.url, {"search": "   bug   "})
        mock_get_labels.assert_called_once_with(page=1, limit=10, search="bug")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)

    def test_get_labels_returns_400_for_invalid_query_params(self):
        response: Response = self.client.get(self.url, {"page": "abc", "limit": -1, "search": 123})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        error_fields = [error["source"]["parameter"] for error in response.data["errors"]]
        self.assertIn("page", error_fields)
        self.assertIn("limit", error_fields)

    @patch("todo.services.label_service.LabelService.get_labels")
    def test_get_labels_returns_with_error_object(self, mock_get_labels: Mock):
        mock_get_labels.return_value = GetLabelsResponse(
            labels=[], total=0, page=1, limit=10, error={"message": ApiErrors.PAGE_NOT_FOUND, "code": "PAGE_NOT_FOUND"}
        )

        response: Response = self.client.get(self.url, {"page": 99, "limit": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "PAGE_NOT_FOUND")

    @patch("todo.services.label_service.LabelService.get_labels")
    def test_get_labels_handles_internal_error(self, mock_get_labels: Mock):
        mock_get_labels.return_value = GetLabelsResponse(
            labels=[],
            total=0,
            page=1,
            limit=10,
            error={"message": ApiErrors.INTERNAL_SERVER_ERROR, "code": "INTERNAL_ERROR"},
        )

        response: Response = self.client.get(self.url, {"page": 1, "limit": 10, "search": "urgent"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["error"]["code"], "INTERNAL_ERROR")

    @patch("todo.services.label_service.LabelService.get_labels")
    def test_get_labels_ignores_extra_params(self, mock_get_labels: Mock):
        mock_get_labels.return_value = GetLabelsResponse(labels=self.label_dtos, total=2, page=1, limit=10)

        response: Response = self.client.get(self.url, {"page": 1, "limit": 10, "extra": "ignored"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_labels.assert_called_once_with(page=1, limit=10, search="")
