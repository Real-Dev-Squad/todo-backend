from http import HTTPStatus
from io import BytesIO
from django.urls import reverse
from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from unittest.mock import patch


class UserProfileAPIIntegrationTest(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("users")
        self.profile_url = reverse("user_profile")

    def test_user_profile_true_requires_auth(self):
        client = self.client.__class__()
        response = client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_user_profile_true_returns_user_info(self):
        response = self.client.get(self.url + "?profile=true")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], str(self.user_id))
        self.assertEqual(data["email"], self.user_data["email"])

    def test_update_profile_picture_requires_auth(self):
        client = self.client.__class__()
        response = client.patch(self.profile_url, data={"picture": BytesIO(b"fake")}, format="multipart")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_update_profile_picture_persists_picture_url(self):
        new_picture = "https://res.cloudinary.com/test_cloud/image/upload/v1/todo/users/abc/profile/picture.png"

        with patch("todo.services.cloudinary_service.CloudinaryService.upload_image", return_value=new_picture):
            response = self.client.patch(
                self.profile_url, data={"picture": BytesIO(b"fake_image_data")}, format="multipart"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        profile_response = self.client.get(self.url + "?profile=true")
        self.assertEqual(profile_response.status_code, HTTPStatus.OK)
        profile_data = profile_response.json()["data"]
        self.assertEqual(profile_data["picture"], new_picture)
