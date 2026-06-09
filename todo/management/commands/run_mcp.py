import os
import json
from datetime import datetime, timezone
from typing import Optional

from django.core.management.base import BaseCommand
from mcp.server.fastmcp import FastMCP

from todo.services.task_service import TaskService
from todo.services.user_service import UserService
from todo.services.team_service import TeamService
from todo.repositories.user_repository import UserRepository
from todo.models.user import UserModel
from todo.dto.task_dto import CreateTaskDTO
from todo.constants.task import TaskPriority, TaskStatus


# Initialize FastMCP Server
mcp = FastMCP("TodoBackend")


def verify_access() -> UserModel:
    """
    Verify that the user configured via environment variables is registered in the database.
    Only allows access to users who are registered in the application database.
    """
    user_id = os.getenv("MCP_USER_ID")
    user_email = os.getenv("MCP_USER_EMAIL")

    if not user_id and not user_email:
        raise ValueError(
            "Access Denied: Neither MCP_USER_ID nor MCP_USER_EMAIL is configured in environment variables. "
            "Please configure one of these variables to access the application."
        )

    collection = UserRepository._get_collection()

    if user_id:
        try:
            from todo.models.common.pyobjectid import PyObjectId

            object_id = PyObjectId(user_id)
            doc = collection.find_one({"_id": object_id})
        except Exception:
            doc = None
    else:
        doc = collection.find_one({"email_id": user_email})

    if not doc:
        detail_msg = f"ID '{user_id}'" if user_id else f"email '{user_email}'"
        raise ValueError(
            f"Access Denied: No registered user found matching {detail_msg}. "
            "Only registered users with existing access to the application can use this MCP server."
        )

    return UserModel(**doc)


@mcp.tool()
def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    team_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> str:
    """
    List and filter tasks. Only shows tasks that the authenticated user has access to.

    Args:
        status: Filter by task status (e.g., 'TODO', 'IN_PROGRESS', 'DONE', 'DEFERRED', 'BACKLOG').
        priority: Filter by task priority (e.g., 'LOW', 'MEDIUM', 'HIGH', 'URGENT').
        team_id: Filter tasks by team ID.
        page: Page number for pagination (starts at 1).
        limit: Max number of tasks to return in a page.
    """
    user = verify_access()
    user_id_str = str(user.id)

    # Map priority string if provided to ensure it is valid
    priority_val = None
    if priority:
        try:
            priority_val = TaskPriority[priority.upper()].value
        except KeyError:
            return f"Error: Invalid priority '{priority}'. Allowed values: LOW, MEDIUM, HIGH, URGENT."

    # Map status string if provided
    status_val = None
    if status:
        try:
            status_val = TaskStatus[status.upper()].value
        except KeyError:
            return f"Error: Invalid status '{status}'. Allowed values: TODO, IN_PROGRESS, DONE, DEFERRED, BACKLOG."

    try:
        response = TaskService.get_tasks(
            page=page,
            limit=limit,
            sort_by="createdAt",
            order="desc",
            user_id=user_id_str,
            team_id=team_id,
            status_filter=status_val,
        )

        if response.error:
            return f"Error: {response.error.get('message')}"

        tasks_data = []
        for t in response.tasks:
            # Optionally filter by priority manually if the repository service didn't support it directly
            if priority_val and t.priority != priority_val:
                continue
            tasks_data.append(t.model_dump(mode="json"))

        return json.dumps(
            {
                "tasks": tasks_data,
                "page": page,
                "limit": limit,
                "has_more": response.links.next is not None if response.links else False,
            },
            indent=2,
        )

    except Exception as e:
        return f"Error occurred while listing tasks: {str(e)}"


@mcp.tool()
def get_task(task_id: str) -> str:
    """
    Get detailed information about a single task by its database ID.
    """
    verify_access()
    try:
        task_dto = TaskService.get_task_by_id(task_id)
        return json.dumps(task_dto.model_dump(mode="json"), indent=2)
    except Exception as e:
        return f"Error: Task not found or retrieval failed. Details: {str(e)}"


@mcp.tool()
def create_task(
    title: str,
    description: Optional[str] = None,
    priority: str = "LOW",
    status: str = "TODO",
    assignee_id: Optional[str] = None,
    assignee_type: Optional[str] = None,
    due_at: Optional[str] = None,
) -> str:
    """
    Create a new task.

    Args:
        title: The title of the task.
        description: Detailed description of the task.
        priority: Priority of the task (LOW, MEDIUM, HIGH, URGENT).
        status: Initial status of the task (TODO, IN_PROGRESS, DONE, DEFERRED, BACKLOG).
        assignee_id: ID of the user or team to assign this task to.
        assignee_type: Either 'user' or 'team'. Required if assignee_id is provided.
        due_at: Due date/time in ISO format (e.g. '2026-06-30T12:00:00Z').
    """
    user = verify_access()
    user_id_str = str(user.id)

    # Validate assignee parameters
    assignee_dict = None
    if assignee_id:
        if not assignee_type or assignee_type.lower() not in ["user", "team"]:
            return "Error: assignee_type must be either 'user' or 'team' when assignee_id is provided."
        assignee_dict = {
            "assignee_id": assignee_id,
            "user_type": assignee_type.lower(),
        }

    # Parse priority and status
    try:
        priority_enum = TaskPriority[priority.upper()]
    except KeyError:
        return f"Error: Invalid priority '{priority}'. Allowed values: LOW, MEDIUM, HIGH, URGENT."

    try:
        status_enum = TaskStatus[status.upper()]
    except KeyError:
        return f"Error: Invalid status '{status}'. Allowed values: TODO, IN_PROGRESS, DONE, DEFERRED, BACKLOG."

    # Parse due_at datetime
    due_dt = None
    if due_at:
        try:
            cleaned_iso = due_at.replace("Z", "+00:00")
            due_dt = datetime.fromisoformat(cleaned_iso)
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
        except Exception:
            return "Error: Invalid due_at format. Please use ISO 8601 format (e.g., '2026-06-30T12:00:00Z')."

    try:
        dto = CreateTaskDTO(
            title=title,
            description=description,
            priority=priority_enum,
            status=status_enum,
            assignee=assignee_dict,
            labels=[],
            dueAt=due_dt,
            createdBy=user_id_str,
        )

        response = TaskService.create_task(dto)
        return json.dumps(
            {
                "message": "Task created successfully",
                "task": response.data.model_dump(mode="json"),
            },
            indent=2,
        )

    except Exception as e:
        return f"Error creating task: {str(e)}"


@mcp.tool()
def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    assignee_type: Optional[str] = None,
    due_at: Optional[str] = None,
) -> str:
    """
    Update fields of an existing task.

    Args:
        task_id: Database ID of the task to update.
        title: New title for the task.
        description: New description for the task.
        priority: New priority (LOW, MEDIUM, HIGH, URGENT).
        status: New status (TODO, IN_PROGRESS, DONE, DEFERRED, BACKLOG).
        assignee_id: New user or team ID to assign the task to. Set to empty string to unassign.
        assignee_type: Required if assignee_id is provided. 'user' or 'team'.
        due_at: New due date in ISO format (e.g. '2026-06-30T12:00:00Z').
    """
    user = verify_access()
    user_id_str = str(user.id)

    validated_data = {}

    if title is not None:
        validated_data["title"] = title
    if description is not None:
        validated_data["description"] = description

    if priority is not None:
        try:
            validated_data["priority"] = TaskPriority[priority.upper()]
        except KeyError:
            return f"Error: Invalid priority '{priority}'. Allowed values: LOW, MEDIUM, HIGH, URGENT."

    if status is not None:
        try:
            validated_data["status"] = TaskStatus[status.upper()].value
        except KeyError:
            return f"Error: Invalid status '{status}'. Allowed values: TODO, IN_PROGRESS, DONE, DEFERRED, BACKLOG."

    if due_at is not None:
        if due_at == "":
            validated_data["dueAt"] = None
        else:
            try:
                cleaned_iso = due_at.replace("Z", "+00:00")
                due_dt = datetime.fromisoformat(cleaned_iso)
                if due_dt.tzinfo is None:
                    due_dt = due_dt.replace(tzinfo=timezone.utc)
                validated_data["dueAt"] = due_dt
            except Exception:
                return "Error: Invalid due_at format. Please use ISO 8601 format (e.g., '2026-06-30T12:00:00Z')."

    if assignee_id is not None:
        if assignee_id == "":
            validated_data["assignee"] = None
        else:
            if not assignee_type or assignee_type.lower() not in ["user", "team"]:
                return "Error: assignee_type must be 'user' or 'team' when assignee_id is provided."
            validated_data["assignee"] = {
                "assignee_id": assignee_id,
                "user_type": assignee_type.lower(),
            }

    if not validated_data:
        return "Error: No update parameters provided."

    try:
        updated_dto = TaskService.update_task_with_assignee_from_dict(
            task_id=task_id,
            validated_data=validated_data,
            user_id=user_id_str,
        )
        return json.dumps(
            {
                "message": "Task updated successfully",
                "task": updated_dto.model_dump(mode="json"),
            },
            indent=2,
        )
    except Exception as e:
        return f"Error updating task: {str(e)}"


@mcp.tool()
def delete_task(task_id: str) -> str:
    """
    Delete a task from the system. Only allowed if the user created it or is assigned to it.
    """
    user = verify_access()
    user_id_str = str(user.id)

    try:
        TaskService.delete_task(task_id, user_id_str)
        return f"Task {task_id} successfully deleted."
    except Exception as e:
        return f"Error deleting task: {str(e)}"


@mcp.tool()
def list_users(page: int = 1, limit: int = 50) -> str:
    """
    List registered users in the application to retrieve their names and IDs.
    """
    verify_access()
    try:
        users, total_count = UserService.get_all_users(page=page, limit=limit)
        users_list = [u.model_dump(mode="json") for u in users]
        return json.dumps(
            {
                "users": users_list,
                "total_count": total_count,
                "page": page,
                "limit": limit,
            },
            indent=2,
        )
    except Exception as e:
        return f"Error listing users: {str(e)}"


@mcp.tool()
def list_teams() -> str:
    """
    List all teams that the active user belongs to, including team IDs.
    """
    user = verify_access()
    user_id_str = str(user.id)

    try:
        response = TeamService.get_user_teams(user_id_str)

        teams_list = [team.model_dump(mode="json") for team in response.teams]
        return json.dumps({"teams": teams_list}, indent=2)
    except Exception as e:
        return f"Error listing teams: {str(e)}"


@mcp.tool()
def search_users(query: str, page: int = 1, limit: int = 10) -> str:
    """
    Search registered users by name or email.

    Args:
        query: Part of user's name or email to search for.
        page: Page number for pagination.
        limit: Max number of search results to return.
    """
    verify_access()
    try:
        users, total_count = UserService.search_users(query=query, page=page, limit=limit)
        users_list = [{"id": str(u.id), "name": u.name, "email": u.email_id} for u in users]
        return json.dumps(
            {
                "results": users_list,
                "total_count": total_count,
                "page": page,
                "limit": limit,
            },
            indent=2,
        )
    except Exception as e:
        return f"Error searching users: {str(e)}"


class Command(BaseCommand):
    help = "Starts the MCP (Model Context Protocol) stdio server for Todo-Backend"

    def handle(self, *args, **options):
        # Prevent any stdout messages from corrupting the stdio communication channel
        # We write a startup notification to stderr instead
        self.stderr.write(self.style.SUCCESS("Starting Todo-Backend MCP Server..."))

        # Run the MCP server over standard input/output (stdio)
        mcp.run("stdio")
