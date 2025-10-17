from http import HTTPStatus
from django.urls import reverse
from bson import ObjectId
from datetime import datetime, timezone
import json

from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.constants.messages import ApiErrors, ValidationErrors


class TeamUpdateIntegrationTests(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.db.teams.delete_many({})
        self.db.user_roles.delete_many({})

        self.team_id = str(ObjectId())
        self.owner_id = str(self.user_id)
        self.admin_id = str(ObjectId())
        self.member_id = str(ObjectId())
        self.non_member_id = str(ObjectId())

        team_doc = {
            "_id": ObjectId(self.team_id),
            "name": "Test Team",
            "description": "Test Description",
            "poc_id": ObjectId(self.member_id),
            "invite_code": "TEST123",
            "created_by": ObjectId(self.owner_id),
            "updated_by": ObjectId(self.owner_id),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_deleted": False,
        }
        self.db.teams.insert_one(team_doc)

        owner_role_doc = {
            "_id": ObjectId(),
            "name": "owner",
            "scope": "TEAM",
            "description": "Team Owner",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        self.db.roles.insert_one(owner_role_doc)

        member_role_doc = {
            "_id": ObjectId(),
            "name": "member",
            "scope": "TEAM",
            "description": "Team Member",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        self.db.roles.insert_one(member_role_doc)

        owner_role = {
            "_id": ObjectId(),
            "user_id": ObjectId(self.owner_id),
            "role_id": owner_role_doc["_id"],
            "role_name": "owner",
            "scope": "TEAM",
            "team_id": ObjectId(self.team_id),
            "is_active": True,
            "created_by": ObjectId(self.owner_id),
            "created_at": datetime.now(timezone.utc),
        }
        self.db.user_roles.insert_one(owner_role)

        authenticated_user_role = {
            "_id": ObjectId(),
            "user_id": str(self.user_id),
            "role_id": owner_role_doc["_id"],
            "role_name": "owner",
            "scope": "TEAM",
            "team_id": str(self.team_id),
            "is_active": True,
            "created_by": str(self.owner_id),
            "created_at": datetime.now(timezone.utc),
        }
        self.db.user_roles.insert_one(authenticated_user_role)

        member_role = {
            "_id": ObjectId(),
            "user_id": self.member_id,
            "role_id": member_role_doc["_id"],
            "role_name": "member",
            "scope": "TEAM",
            "team_id": self.team_id,
            "is_active": True,
            "created_by": self.owner_id,
            "created_at": datetime.now(timezone.utc),
        }
        self.db.user_roles.insert_one(member_role)

        self.db.users.insert_one(
            {
                "_id": ObjectId(self.member_id),
                "google_id": "member_google_id",
                "email_id": "member@example.com",
                "name": "Member User",
                "picture": "member_picture",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
            }
        )

        self.db.users.insert_one(
            {
                "_id": ObjectId(self.non_member_id),
                "google_id": "non_member_google_id",
                "email_id": "nonmember@example.com",
                "name": "Non Member User",
                "picture": "non_member_picture",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
            }
        )

        self.existing_team_id = self.team_id
        self.non_existent_id = str(ObjectId())
        self.invalid_team_id = "invalid-team-id"

    def test_update_team_success_by_owner(self):
        url = reverse("team_detail", args=[self.existing_team_id])
        response = self.client.patch(
            url,
            data=json.dumps({"poc_id": self.member_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["poc_id"], self.member_id)
        self.assertNotIn("invite_code", data)

    def test_update_team_unauthorized_user(self):
        other_user_id = ObjectId()
        self._create_test_user(other_user_id)
        self._set_auth_cookies()

        url = reverse("team_detail", args=[self.existing_team_id])
        response = self.client.patch(url, data=json.dumps({"name": "Updated Team"}), content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        data = response.json()
        self.assertEqual(data["detail"], ApiErrors.UNAUTHORIZED_TITLE)

    def test_update_team_empty_payload(self):
        url = reverse("team_detail", args=[self.existing_team_id])
        response = self.client.patch(url, data=json.dumps({}), content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertIn("non_field_errors", data["errors"])
        self.assertIn(ValidationErrors.POC_NOT_PROVIDED, str(data["errors"]["non_field_errors"]))

    def test_update_team_invalid_poc_id_format(self):
        url = reverse("team_detail", args=[self.existing_team_id])
        response = self.client.patch(url, data=json.dumps({"poc_id": "invalid-id"}), content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertIn("poc_id", data["errors"])
        self.assertIn(ValidationErrors.INVALID_OBJECT_ID.format("invalid-id"), str(data["errors"]["poc_id"]))
