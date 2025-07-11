from todo.models.user import UserModel
from todo.repositories.user_repository import UserRepository
from todo.constants.messages import ValidationErrors, RepositoryErrors
from todo.exceptions.google_auth_exceptions import GoogleUserNotFoundException, GoogleAPIException
from rest_framework.exceptions import ValidationError as DRFValidationError
from typing import List, Tuple


class UserService:
    @classmethod
    def create_or_update_user(cls, google_user_data: dict) -> UserModel:
        try:
            cls._validate_google_user_data(google_user_data)
            return UserRepository.create_or_update(google_user_data)
        except (GoogleUserNotFoundException, GoogleAPIException, DRFValidationError):
            raise
        except Exception as e:
            raise GoogleAPIException(RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(str(e))) from e

    @classmethod
    def get_user_by_id(cls, user_id: str) -> UserModel:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise GoogleUserNotFoundException()
        return user

    @classmethod
    def search_users(cls, query: str, page: int = 1, limit: int = 10) -> Tuple[List[UserModel], int]:
        """
        Search users by name or email using fuzzy search
        """
        try:
            cls._validate_search_params(query, page, limit)
            return UserRepository.search_users(query, page, limit)
        except (GoogleUserNotFoundException, GoogleAPIException, DRFValidationError):
            raise
        except Exception as e:
            raise GoogleAPIException(f"User search failed: {str(e)}") from e

    @classmethod
    def search_users_by_name(cls, name: str, page: int = 1, limit: int = 10) -> Tuple[List[UserModel], int]:
        """
        Search users by name only
        """
        try:
            cls._validate_search_params(name, page, limit)
            return UserRepository.search_users_by_name(name, page, limit)
        except (GoogleUserNotFoundException, GoogleAPIException, DRFValidationError):
            raise
        except Exception as e:
            raise GoogleAPIException(f"User search by name failed: {str(e)}") from e

    @classmethod
    def search_users_by_email(cls, email: str, page: int = 1, limit: int = 10) -> Tuple[List[UserModel], int]:
        """
        Search users by email only
        """
        try:
            cls._validate_search_params(email, page, limit)
            return UserRepository.search_users_by_email(email, page, limit)
        except (GoogleUserNotFoundException, GoogleAPIException, DRFValidationError):
            raise
        except Exception as e:
            raise GoogleAPIException(f"User search by email failed: {str(e)}") from e

    @classmethod
    def get_all_users(cls, page: int = 1, limit: int = 10) -> Tuple[List[UserModel], int]:
        """
        Get all users with pagination
        """
        try:
            cls._validate_pagination_params(page, limit)
            return UserRepository.get_all_users(page, limit)
        except (GoogleUserNotFoundException, GoogleAPIException, DRFValidationError):
            raise
        except Exception as e:
            raise GoogleAPIException(f"Failed to get users: {str(e)}") from e

    @classmethod
    def _validate_google_user_data(cls, google_user_data: dict) -> None:
        validation_errors = {}

        if not google_user_data.get("google_id"):
            validation_errors["google_id"] = ValidationErrors.MISSING_GOOGLE_ID

        if not google_user_data.get("email"):
            validation_errors["email"] = ValidationErrors.MISSING_EMAIL

        if not google_user_data.get("name"):
            validation_errors["name"] = ValidationErrors.MISSING_NAME

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
    def _validate_pagination_params(cls, page: int, limit: int) -> None:
        validation_errors = {}

        if page < 1:
            validation_errors["page"] = ValidationErrors.PAGE_POSITIVE

        if limit < 1:
            validation_errors["limit"] = ValidationErrors.LIMIT_POSITIVE

        if limit > 100:
            validation_errors["limit"] = ValidationErrors.MAX_LIMIT_EXCEEDED.format(100)

        if validation_errors:
            raise DRFValidationError(validation_errors)
