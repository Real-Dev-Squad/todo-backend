import json
import os
from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId

from todo.models.user import UserModel
from todo.dto.task_dto import TaskDTO
from todo.dto.user_dto import UserDTO, UsersDTO
from todo.dto.responses.get_tasks_response import GetTasksResponse
from todo.dto.responses.create_task_response import CreateTaskResponse
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.dto.team_dto import TeamDTO
from todo.constants.task import TaskPriority, TaskStatus
from todo.models.common.pyobjectid import PyObjectId

# Import functions under test
from todo.management.commands.run_mcp import (
    verify_access,
    list_tasks,
    get_task,
    create_task,
    update_task,
    delete_task,
    list_users,
    list_teams,
    search_users,
)


class TestMcpServer(TestCase):
    def setUp(self):
        self.mock_user_id = "60c72b2f9b1d8e3d8f8e8f8e"
        self.mock_user = UserModel(
            _id=PyObjectId(self.mock_user_id),
            google_id="google_123",
            email_id="user@example.com",
            name="Test User",
            picture="http://example.com/pic.jpg",
            created_at=datetime.now(timezone.utc),
        )

        self.env_patcher = patch.dict(os.environ, {})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def create_mock_task_dto(self, task_id="task_123", title="Sample Task"):
        return TaskDTO(
            id=task_id,
            displayId="T-1",
            title=title,
            description="Task Description",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            assignee=None,
            isAcknowledged=False,
            labels=[],
            startedAt=None,
            dueAt=None,
            deferredDetails=None,
            in_watchlist=False,
            createdAt=datetime(2026, 6, 10, tzinfo=timezone.utc),
            updatedAt=None,
            createdBy=UserDTO(id=self.mock_user_id, name="Test User"),
            updatedBy=None,
        )

    @patch("todo.management.commands.run_mcp.UserRepository._get_collection")
    def test_verify_access_no_env(self, mock_get_collection):
        # Neither MCP_USER_ID nor MCP_USER_EMAIL is configured
        if "MCP_USER_ID" in os.environ:
            del os.environ["MCP_USER_ID"]
        if "MCP_USER_EMAIL" in os.environ:
            del os.environ["MCP_USER_EMAIL"]

        with self.assertRaises(ValueError) as context:
            verify_access()
        self.assertIn("Neither MCP_USER_ID nor MCP_USER_EMAIL is configured", str(context.exception))

    @patch("todo.management.commands.run_mcp.UserRepository._get_collection")
    def test_verify_access_by_id_success(self, mock_get_collection):
        os.environ["MCP_USER_ID"] = self.mock_user_id

        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "_id": ObjectId(self.mock_user_id),
            "google_id": "google_123",
            "email_id": "user@example.com",
            "name": "Test User",
            "picture": "http://example.com/pic.jpg",
            "created_at": datetime.now(timezone.utc),
        }
        mock_get_collection.return_value = mock_collection

        user = verify_access()
        self.assertEqual(str(user.id), self.mock_user_id)
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(self.mock_user_id)})

    @patch("todo.management.commands.run_mcp.UserRepository._get_collection")
    def test_verify_access_by_email_success(self, mock_get_collection):
        os.environ["MCP_USER_EMAIL"] = "user@example.com"

        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "_id": ObjectId(self.mock_user_id),
            "google_id": "google_123",
            "email_id": "user@example.com",
            "name": "Test User",
            "picture": "http://example.com/pic.jpg",
            "created_at": datetime.now(timezone.utc),
        }
        mock_get_collection.return_value = mock_collection

        user = verify_access()
        self.assertEqual(user.email_id, "user@example.com")
        mock_collection.find_one.assert_called_once_with({"email_id": "user@example.com"})

    @patch("todo.management.commands.run_mcp.UserRepository._get_collection")
    def test_verify_access_not_found(self, mock_get_collection):
        os.environ["MCP_USER_EMAIL"] = "user@example.com"
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_get_collection.return_value = mock_collection

        with self.assertRaises(ValueError) as context:
            verify_access()
        self.assertIn("No registered user found matching email 'user@example.com'", str(context.exception))

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.TaskService.get_tasks")
    def test_list_tasks_success(self, mock_get_tasks, mock_verify):
        mock_verify.return_value = self.mock_user
        mock_task = self.create_mock_task_dto()

        mock_get_tasks.return_value = GetTasksResponse(tasks=[mock_task], links=None)

        result_str = list_tasks()
        result = json.loads(result_str)

        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(result["tasks"][0]["title"], "Sample Task")
        mock_get_tasks.assert_called_once()

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.TaskService.get_task_by_id")
    def test_get_task_success(self, mock_get_task_by_id, mock_verify):
        mock_verify.return_value = self.mock_user
        mock_task = self.create_mock_task_dto()

        mock_get_task_by_id.return_value = mock_task

        result_str = get_task("task_123")
        try:
            result = json.loads(result_str)
        except Exception as e:
            print("\n--- DEBUG GET_TASK OUTPUT ---")
            print(result_str)
            print("-----------------------------\n")
            raise e

        self.assertEqual(result["id"], "task_123")
        self.assertEqual(result["title"], "Sample Task")

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.TaskService.create_task")
    def test_create_task_success(self, mock_create_task, mock_verify):
        mock_verify.return_value = self.mock_user
        mock_task = self.create_mock_task_dto(task_id="task_created", title="New Task")

        mock_create_task.return_value = CreateTaskResponse(data=mock_task)

        result_str = create_task(title="New Task", priority="HIGH", status="IN_PROGRESS")
        result = json.loads(result_str)

        self.assertEqual(result["task"]["id"], "task_created")
        self.assertEqual(result["task"]["displayId"], "T-1")
        mock_create_task.assert_called_once()

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.TaskService.update_task_with_assignee_from_dict")
    def test_update_task_success(self, mock_update_task, mock_verify):
        mock_verify.return_value = self.mock_user
        mock_task = self.create_mock_task_dto(task_id="task_123")
        mock_task.status = TaskStatus.DONE
        mock_task.priority = TaskPriority.MEDIUM

        mock_update_task.return_value = mock_task

        result_str = update_task(task_id="task_123", status="DONE", priority="MEDIUM")
        result = json.loads(result_str)

        self.assertEqual(result["task"]["id"], "task_123")
        self.assertEqual(result["task"]["status"], "DONE")
        mock_update_task.assert_called_once()

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.TaskService.delete_task")
    def test_delete_task_success(self, mock_delete_task, mock_verify):
        mock_verify.return_value = self.mock_user

        result = delete_task("task_123")
        self.assertIn("successfully deleted", result)
        mock_delete_task.assert_called_once_with("task_123", self.mock_user_id)

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.UserService.get_all_users")
    def test_list_users_success(self, mock_get_all_users, mock_verify):
        mock_verify.return_value = self.mock_user
        mock_user_dto = UsersDTO(id="user_234", name="Other User")
        mock_get_all_users.return_value = ([mock_user_dto], 1)

        result_str = list_users()
        result = json.loads(result_str)

        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["users"][0]["name"], "Other User")

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.TeamService.get_user_teams")
    def test_list_teams_success(self, mock_get_user_teams, mock_verify):
        mock_verify.return_value = self.mock_user

        mock_team = TeamDTO(
            id="team_123",
            name="Development Team",
            description="Devs",
            poc_id=self.mock_user_id,
            invite_code="XYZ123",
            created_by=self.mock_user_id,
            updated_by=self.mock_user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_get_user_teams.return_value = GetUserTeamsResponse(teams=[mock_team])

        result_str = list_teams()
        result = json.loads(result_str)

        self.assertEqual(len(result["teams"]), 1)
        self.assertEqual(result["teams"][0]["name"], "Development Team")

    @patch("todo.management.commands.run_mcp.verify_access")
    @patch("todo.management.commands.run_mcp.UserService.search_users")
    def test_search_users_success(self, mock_search_users, mock_verify):
        mock_verify.return_value = self.mock_user

        mock_user_match = UserModel(
            _id=PyObjectId("60c72b2f9b1d8e3d8f8e8f8a"),
            google_id="google_456",
            email_id="searched@example.com",
            name="Searched User",
            picture=None,
            created_at=datetime.now(timezone.utc),
        )
        mock_search_users.return_value = ([mock_user_match], 1)

        result_str = search_users(query="Searched")
        result = json.loads(result_str)

        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["results"][0]["name"], "Searched User")
        self.assertEqual(result["results"][0]["email"], "searched@example.com")
