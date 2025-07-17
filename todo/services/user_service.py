from todo.models.user import UserModel
from todo.repositories.user_repository import UserRepository
from todo.constants.messages import ValidationErrors, RepositoryErrors
from todo.exceptions.auth_exceptions import (
    UserNotFoundException,
    APIException,
)
from rest_framework.exceptions import ValidationError as DRFValidationError
from typing import List, Tuple
from todo.dto.user_dto import UserDTO, UsersDTO


class UserService:
    @classmethod
    def create_or_update_user(cls, google_user_data: dict) -> UserModel:
        try:
            cls._validate_google_user_data(google_user_data)
            return UserRepository.create_or_update(google_user_data)
        except (UserNotFoundException, APIException, DRFValidationError):
            raise
        except Exception as e:
            raise APIException(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(str(e))) from e

    @classmethod
    def get_user_by_id(cls, user_id: str) -> UserModel:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return user

    @classmethod
    def search_users(cls, query: str, page: int = 1, limit: int = 10) -> Tuple[List[UserModel], int]:
        """
        Search users by name or email using fuzzy search
        """
        cls._validate_search_params(query, page, limit)
        return UserRepository.search_users(query, page, limit)

    @classmethod
    def get_users_by_ids(cls, user_ids: list[str]) -> list[UserDTO]:
        users = []
        for user_id in user_ids:
            user = UserRepository.get_by_id(user_id)
            if user:
                users.append(
                    UserDTO(
                        id=str(user.id),
                        name=user.name,
                        email_id=user.email_id,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                    )
                )
        return users

    @classmethod
    def get_users_by_team_id(cls, team_id: str) -> list[UserDTO]:
        from todo.repositories.team_repository import UserTeamDetailsRepository

        users_and_added_on = UserTeamDetailsRepository.get_users_and_added_on_by_team_id(team_id)
        user_ids = [entry["user_id"] for entry in users_and_added_on]
        added_on_map = {entry["user_id"]: entry["added_on"] for entry in users_and_added_on}
        users = cls.get_users_by_ids(user_ids)
        # Attach addedOn to each user dto
        for user in users:
            user.addedOn = added_on_map.get(user.id)
            # Compute tasksAssignedCount: tasks assigned to both user and team
            from todo.repositories.assignee_task_details_repository import (
                AssigneeTaskDetailsRepository,
            )

            user_task_ids = set(
                [
                    str(assignment.task_id)
                    for assignment in AssigneeTaskDetailsRepository.get_by_assignee_id(user.id, "user")
                ]
            )
            team_task_ids = set(
                [
                    str(assignment.task_id)
                    for assignment in AssigneeTaskDetailsRepository.get_by_assignee_id(team_id, "team")
                ]
            )
            user.tasksAssignedCount = len(user_task_ids & team_task_ids)
        return users

    @classmethod
    def _validate_google_user_data(cls, google_user_data: dict) -> None:
        validation_errors = {}

        if not google_user_data.get("google_id"):
            validation_errors["google_id"] = ValidationErrors.MISSING_GOOGLE_ID

        if not google_user_data.get("email"):
            validation_errors["email"] = ValidationErrors.MISSING_EMAIL

        if not google_user_data.get("name"):
            validation_errors["name"] = ValidationErrors.MISSING_NAME

        if not google_user_data.get("picture"):
            validation_errors["picture"] = ValidationErrors.MISSING_PICTURE

        if validation_errors:
            raise DRFValidationError(validation_errors)

    @classmethod
    def _validate_search_params(cls, query: str, page: int, limit: int) -> None:
        validation_errors = {}

        if not query or not query.strip():
            validation_errors["query"] = "Search query cannot be empty"

        if page < 1:
            validation_errors["page"] = ValidationErrors.PAGE_POSITIVE

        if limit < 1:
            validation_errors["limit"] = ValidationErrors.LIMIT_POSITIVE

        if limit > 100:
            validation_errors["limit"] = ValidationErrors.MAX_LIMIT_EXCEEDED.format(100)

        if validation_errors:
            raise DRFValidationError(validation_errors)

    @classmethod
    def get_all_users(cls, page: int = 1, limit: int = 10) -> List[UsersDTO]:
        """
        Get all users with pagination
        """
        users, total_count = UserRepository.get_all_users(page, limit)
        user_dtos = [
            UsersDTO(
                id=str(user.id),
                name=user.name,
            )
            for user in users
        ]

        return user_dtos, total_count
