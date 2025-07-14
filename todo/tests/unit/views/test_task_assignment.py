from unittest.mock import patch
from rest_framework import status
from bson import ObjectId
from datetime import datetime, timezone

from todo.tests.integration.base_mongo_test import AuthenticatedMongoTestCase
from todo.dto.task_assignment_dto import TaskAssignmentResponseDTO
from todo.dto.responses.create_task_assignment_response import CreateTaskAssignmentResponse


class TaskAssignmentViewTests(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/v1/task-assignments"
        self.task_id = str(ObjectId())
        self.team_id = str(ObjectId())

        self.valid_user_assignment_payload = {
            "task_id": self.task_id,
            "assignee_id": str(self.user_id),
            "user_type": "user",
        }

        self.valid_team_assignment_payload = {"task_id": self.task_id, "assignee_id": self.team_id, "user_type": "team"}

    @patch("todo.services.task_assignment_service.TaskAssignmentService.create_task_assignment")
    def test_create_user_assignment_success(self, mock_create_assignment):
        # Mock service response
        response_dto = TaskAssignmentResponseDTO(
            id=str(ObjectId()),
            task_id=self.task_id,
            assignee_id=str(self.user_id),
            user_type="user",
            assignee_name="Test User",
            is_active=True,
            created_by=str(self.user_id),
            updated_by=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )
        mock_create_assignment.return_value = CreateTaskAssignmentResponse(data=response_dto)

        response = self.client.post(self.url, data=self.valid_user_assignment_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["user_type"], "user")
        mock_create_assignment.assert_called_once()

    @patch("todo.services.task_assignment_service.TaskAssignmentService.create_task_assignment")
    def test_create_team_assignment_success(self, mock_create_assignment):
        # Mock service response
        response_dto = TaskAssignmentResponseDTO(
            id=str(ObjectId()),
            task_id=self.task_id,
            assignee_id=self.team_id,
            user_type="team",
            assignee_name="Test Team",
            is_active=True,
            created_by=str(self.user_id),
            updated_by=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )
        mock_create_assignment.return_value = CreateTaskAssignmentResponse(data=response_dto)

        response = self.client.post(self.url, data=self.valid_team_assignment_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["user_type"], "team")
        mock_create_assignment.assert_called_once()

    def test_create_assignment_invalid_user_type(self):
        invalid_payload = {"task_id": self.task_id, "assignee_id": str(self.user_id), "user_type": "invalid_type"}

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)

    def test_create_assignment_invalid_task_id(self):
        invalid_payload = {"task_id": "invalid_id", "assignee_id": str(self.user_id), "user_type": "user"}

        response = self.client.post(self.url, data=invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)

    def test_create_assignment_missing_required_fields(self):
        incomplete_payload = {
            "task_id": self.task_id,
            # Missing assignee_id and user_type
        }

        response = self.client.post(self.url, data=incomplete_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)


class TaskAssignmentDetailViewTests(AuthenticatedMongoTestCase):
    def setUp(self):
        super().setUp()
        self.task_id = str(ObjectId())
        self.url = f"/v1/task-assignments/{self.task_id}"

    @patch("todo.services.task_assignment_service.TaskAssignmentService.get_task_assignment")
    def test_get_task_assignment_success(self, mock_get_assignment):
        # Mock service response
        response_dto = TaskAssignmentResponseDTO(
            id=str(ObjectId()),
            task_id=self.task_id,
            assignee_id=str(self.user_id),
            user_type="user",
            assignee_name="Test User",
            is_active=True,
            created_by=str(self.user_id),
            updated_by=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )
        mock_get_assignment.return_value = response_dto

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], self.task_id)
        mock_get_assignment.assert_called_once_with(self.task_id)

    @patch("todo.services.task_assignment_service.TaskAssignmentService.get_task_assignment")
    def test_get_task_assignment_not_found(self, mock_get_assignment):
        # Mock service returning None
        mock_get_assignment.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("message", response.data)

    @patch("todo.services.task_assignment_service.TaskAssignmentService.delete_task_assignment")
    def test_delete_task_assignment_success(self, mock_delete_assignment):
        # Mock successful deletion
        mock_delete_assignment.return_value = True

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_delete_assignment.assert_called_once_with(self.task_id, str(self.user_id))

    @patch("todo.services.task_assignment_service.TaskAssignmentService.delete_task_assignment")
    def test_delete_task_assignment_not_found(self, mock_delete_assignment):
        # Mock unsuccessful deletion
        mock_delete_assignment.return_value = False

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("message", response.data)
