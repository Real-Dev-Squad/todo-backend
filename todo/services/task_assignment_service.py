from typing import Optional

from todo.dto.assignee_task_details_dto import AssigneeTaskDetailsDTO, CreateAssigneeTaskDetailsDTO
from todo.dto.task_assignment_dto import TaskAssignmentResponseDTO
from todo.dto.responses.create_task_assignment_response import CreateTaskAssignmentResponse
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.task_assignment_repository import TaskAssignmentRepository
from todo.repositories.task_repository import TaskRepository
from todo.repositories.user_repository import UserRepository
from todo.repositories.team_repository import TeamRepository
from todo.exceptions.user_exceptions import UserNotFoundException
from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.repositories.assignee_task_details_repository import AssigneeTaskDetailsRepository
from todo.models.assignee_task_details import AssigneeTaskDetailsModel


class TaskAssignmentService:
    @classmethod
    def create_task_assignment(cls, dto: CreateAssigneeTaskDetailsDTO, user_id: str) -> CreateTaskAssignmentResponse:
        """
        Create a new task assignment with validation for task, user, and team existence.
        """
        # Validate task exists
        task = TaskRepository.get_by_id(dto.task_id)
        if not task:
            raise TaskNotFoundException(dto.task_id)

        # Validate assignee exists based on user_type
        if dto.relation_type == "user":
            assignee = UserRepository.get_by_id(dto.assignee_id)
            if not assignee:
                raise UserNotFoundException(dto.assignee_id)
            assignee_name = assignee.name
        elif dto.relation_type == "team":
            assignee = TeamRepository.get_by_id(dto.assignee_id)
            if not assignee:
                raise ValueError(f"Team not found: {dto.assignee_id}")
            assignee_name = assignee.name
        else:
            raise ValueError("Invalid relation_type")

        # Check if task already has an active assignment
        existing_assignment = AssigneeTaskDetailsRepository.get_by_task_id(dto.task_id)
        if existing_assignment:
            # Update existing assignment
            updated_assignment = AssigneeTaskDetailsRepository.update_assignment(
                dto.task_id, dto.assignee_id, dto.relation_type, user_id
            )
            if not updated_assignment:
                raise ValueError("Failed to update task assignment")

            assignment = updated_assignment
        else:
            # Create new assignment
            task_assignment = AssigneeTaskDetailsModel(
                task_id=PyObjectId(dto.task_id),
                assignee_id=PyObjectId(dto.assignee_id),
                relation_type=dto.relation_type,
                created_by=PyObjectId(user_id),
                updated_by=None,
            )

            assignment = AssigneeTaskDetailsRepository.create(task_assignment)

        # Also insert into assignee_task_details if this is a team assignment
        if dto.relation_type == "team":
            AssigneeTaskDetailsRepository.create(
                AssigneeTaskDetailsModel(
                    assignee_id=PyObjectId(dto.assignee_id),
                    task_id=PyObjectId(dto.task_id),
                    relation_type="team",
                    is_action_taken=False,
                    is_active=True,
                    created_by=PyObjectId(user_id),
                    updated_by=None,
                )
            )

        # Prepare response
        response_dto = AssigneeTaskDetailsDTO(
            id=str(assignment.id),
            task_id=str(assignment.task_id),
            assignee_id=str(assignment.assignee_id),
            relation_type=assignment.relation_type,
            is_action_taken=assignment.is_action_taken,
            assignee_name=assignee_name,
            is_active=assignment.is_active,
            created_by=str(assignment.created_by),
            created_at=assignment.created_at,
        )

        return CreateTaskAssignmentResponse(data=response_dto)

    @classmethod
    def get_task_assignment(cls, task_id: str) -> Optional[TaskAssignmentResponseDTO]:
        """
        Get task assignment by task ID.
        """
        assignment = TaskAssignmentRepository.get_by_task_id(task_id)
        if not assignment:
            return None

        # Get assignee name
        if assignment.user_type == "user":
            assignee = UserRepository.get_by_id(str(assignment.assignee_id))
            assignee_name = assignee.name if assignee else "Unknown User"
        elif assignment.user_type == "team":
            assignee = TeamRepository.get_by_id(str(assignment.assignee_id))
            assignee_name = assignee.name if assignee else "Unknown Team"
        else:
            assignee_name = "Unknown"

        return TaskAssignmentResponseDTO(
            id=str(assignment.id),
            task_id=str(assignment.task_id),
            assignee_id=str(assignment.assignee_id),
            user_type=assignment.user_type,
            assignee_name=assignee_name,
            is_active=assignment.is_active,
            created_by=str(assignment.created_by),
            updated_by=str(assignment.updated_by) if assignment.updated_by else None,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )

    @classmethod
    def delete_task_assignment(cls, task_id: str, user_id: str) -> bool:
        """
        Delete task assignment by task ID.
        """
        return TaskAssignmentRepository.delete_assignment(task_id, user_id)
